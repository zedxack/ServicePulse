"""
ServicePulse - Network Incident Processor
Evaluates probe results, handles consecutive failure counters, transitions device status,
manages verified OutageInterval records, and coordinates incident creation and auto-recovery.
Author: Muhammadyusuf Usmonov
"""
from datetime import timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.incident import Incident, IncidentEvent
from backend.app.models.inventory import Device
from backend.app.models.monitoring import (
    DeviceMonitoringConfig,
    DeviceStateTransition,
    OutageInterval,
)
from backend.app.models.network import NetworkCheck
from backend.app.schemas.incident import IncidentCreate
from backend.app.schemas.monitoring import ProbeResult
from backend.app.schemas.notification import NotificationCreate
from backend.app.services.event_outbox_service import EventOutboxService
from backend.app.services.incident_service import IncidentService
from backend.app.services.notification_service import NotificationService
from backend.app.services.ws_manager import ws_manager


class NetworkIncidentProcessor:
    """
    Translates raw network probe observations into state transitions,
    outage intervals, deduplicated incidents, and recovery events.
    """

    @staticmethod
    async def process_probe_result(
        probe_result: ProbeResult,
        device: Device,
        config: DeviceMonitoringConfig,
        db: AsyncSession
    ) -> Optional[Incident]:
        """
        Process a probe result:
        1. Persist NetworkCheck record.
        2. Evaluate success vs failure.
        3. Handle state transitions and outage intervals.
        4. Trigger incident creation / deduplication or auto-recovery.
        """
        now = probe_result.checked_at

        # 1. Record NetworkCheck entry in DB
        nc = NetworkCheck(
            device_id=device.id,
            check_type=probe_result.check_type,
            port=probe_result.port,
            is_successful=probe_result.is_successful,
            response_time_ms=probe_result.response_time_ms,
            packet_loss_percent=probe_result.packet_loss_percent,
            error_message=probe_result.error_message,
            checked_at=now,
        )
        db.add(nc)

        incident_result: Optional[Incident] = None

        if not probe_result.is_successful:
            # -------------------------------------------------------------
            # PROBE FAILURE FLOW
            # -------------------------------------------------------------
            device.consecutive_failures += 1
            threshold = config.consecutive_failure_threshold

            if device.consecutive_failures >= threshold:
                # Transition to OFFLINE if not already offline
                if device.status != "offline":
                    old_status = device.status
                    device.status = "offline"

                    # Record state transition
                    trans = DeviceStateTransition(
                        device_id=device.id,
                        from_status=old_status,
                        to_status="offline",
                        trigger_reason=f"Reached threshold of {device.consecutive_failures} consecutive probe failures",
                        consecutive_failures=device.consecutive_failures,
                        transition_at=now,
                    )
                    db.add(trans)

                    # Start verified OutageInterval
                    outage = OutageInterval(
                        organization_id=device.organization_id,
                        device_id=device.id,
                        started_at=now,
                        is_planned=False,
                        root_cause=probe_result.error_message or "Network probe timeout",
                    )
                    db.add(outage)
                    await db.flush()

                    if device.organization_id:
                        await EventOutboxService.record_worker_event(
                            db=db,
                            organization_id=device.organization_id,
                            event_type="device:status_change",
                            data={
                                "device_id": device.id,
                                "device_name": device.name,
                                "old_status": old_status,
                                "new_status": "offline",
                            },
                        )
                        await ws_manager.broadcast_to_org(
                            device.organization_id,
                            "device:status_change",
                            {
                                "device_id": device.id,
                                "device_name": device.name,
                                "old_status": old_status,
                                "new_status": "offline",
                            },
                        )
                        await NotificationService.create_notification(
                            db=db,
                            notif_in=NotificationCreate(
                                organization_id=device.organization_id,
                                title=f"Device Offline: {device.name}",
                                message=f"Device '{device.name}' ({device.ip_address}) failed {device.consecutive_failures} consecutive probes.",
                                severity="error",
                                category="device",
                                fingerprint=f"dev_offline_notif:{device.id}",
                                data={"device_id": device.id, "ip_address": device.ip_address},
                            ),
                        )

                # Create or Deduplicate Incident
                inc_title = f"Device unreachable: {device.name} ({device.ip_address})"
                inc_in = IncidentCreate(
                    organization_id=device.organization_id,
                    device_id=device.id,
                    title=inc_title,
                    description=(
                        f"Device '{device.name}' at {device.ip_address} failed {device.consecutive_failures} "
                        f"consecutive network probes. Error: {probe_result.error_message or 'Host unreachable'}."
                    ),
                    severity="critical",
                    fingerprint=f"dev_offline:{device.id}",
                )
                incident_result = await IncidentService.create_or_deduplicate_incident(
                    inc_in=inc_in,
                    creator=None,
                    db=db,
                    scoped_org_id=device.organization_id,
                )

                # Link incident to open outage interval if present
                open_outage_q = select(OutageInterval).where(
                    OutageInterval.device_id == device.id,
                    OutageInterval.ended_at.is_(None)
                ).order_by(OutageInterval.started_at.desc()).limit(1)
                open_outage = (await db.execute(open_outage_q)).scalar_one_or_none()
                if open_outage and not open_outage.incident_id:
                    open_outage.incident_id = incident_result.id

                # Trigger automated remediation rules
                from backend.app.services.remediation_service import RemediationService
                await RemediationService.evaluate_incident_remediation(incident_result.id, db)

            elif device.consecutive_failures > 0 and device.status == "online":
                # Single failure - mark warning but do not declare outage yet
                old_status = device.status
                device.status = "warning"
                trans = DeviceStateTransition(
                    device_id=device.id,
                    from_status=old_status,
                    to_status="warning",
                    trigger_reason=f"Intermittent probe failure ({device.consecutive_failures}/{threshold})",
                    consecutive_failures=device.consecutive_failures,
                    transition_at=now,
                )
                db.add(trans)

        else:
            # -------------------------------------------------------------
            # PROBE SUCCESS FLOW
            # -------------------------------------------------------------
            if device.status in ("offline", "warning"):
                old_status = device.status
                device.status = "online"

                # Record state transition
                trans = DeviceStateTransition(
                    device_id=device.id,
                    from_status=old_status,
                    to_status="online",
                    trigger_reason="Network probe succeeded",
                    consecutive_failures=0,
                    transition_at=now,
                )
                db.add(trans)

                # Close active OutageInterval if device was offline
                if old_status == "offline":
                    outage_q = select(OutageInterval).where(
                        OutageInterval.device_id == device.id,
                        OutageInterval.ended_at.is_(None)
                    ).order_by(OutageInterval.started_at.desc()).limit(1)
                    active_outage = (await db.execute(outage_q)).scalar_one_or_none()
                    if active_outage:
                        active_outage.ended_at = now
                        started = active_outage.started_at
                        if started.tzinfo is None:
                            started = started.replace(tzinfo=timezone.utc)
                        active_outage.duration_seconds = max(0.0, (now - started).total_seconds())

                    # Auto-resolve or record recovery event on active incident
                    active_inc_q = select(Incident).where(
                        Incident.device_id == device.id,
                        Incident.status.in_(["open", "acknowledged", "in_progress"]),
                        Incident.fingerprint == f"dev_offline:{device.id}"
                    ).order_by(Incident.first_seen_at.desc()).limit(1)
                    active_inc = (await db.execute(active_inc_q)).scalar_one_or_none()

                    if active_inc:
                        rec_msg = (
                            f"Device '{device.name}' responded successfully to network probe "
                            f"(latency: {probe_result.response_time_ms}ms). Connectivity restored."
                        )
                        recovery_event = IncidentEvent(
                            incident_id=active_inc.id,
                            event_type="recovery",
                            message=rec_msg,
                            created_at=now,
                        )
                        db.add(recovery_event)

                        if settings.AUTO_RESOLVE_INCIDENT_ON_RECOVERY:
                            active_inc.status = "resolved"
                            active_inc.resolved_at = now
                            active_inc.resolution_notes = f"Auto-resolved: {rec_msg}"
                            active_inc.active_dedup_key = None  # Clear key so future failures trigger new incidents
                            resolved_event = IncidentEvent(
                                incident_id=active_inc.id,
                                event_type="resolved",
                                message=f"Automated Recovery: {active_inc.resolution_notes}",
                                created_at=now,
                            )
                            db.add(resolved_event)
                            if device.organization_id:
                                await EventOutboxService.record_worker_event(
                                    db=db,
                                    organization_id=device.organization_id,
                                    event_type="incident:resolved",
                                    data={
                                        "id": active_inc.id,
                                        "status": "resolved",
                                        "resolution_notes": active_inc.resolution_notes,
                                    },
                                )
                                await ws_manager.broadcast_to_org(
                                    device.organization_id,
                                    "incident:resolved",
                                    {
                                        "id": active_inc.id,
                                        "status": "resolved",
                                        "resolution_notes": active_inc.resolution_notes,
                                    },
                                )

                    if device.organization_id:
                        await EventOutboxService.record_worker_event(
                            db=db,
                            organization_id=device.organization_id,
                            event_type="device:status_change",
                            data={
                                "device_id": device.id,
                                "device_name": device.name,
                                "old_status": old_status,
                                "new_status": "online",
                            },
                        )
                        await ws_manager.broadcast_to_org(
                            device.organization_id,
                            "device:status_change",
                            {
                                "device_id": device.id,
                                "device_name": device.name,
                                "old_status": old_status,
                                "new_status": "online",
                            },
                        )
                        await NotificationService.create_notification(
                            db=db,
                            notif_in=NotificationCreate(
                                organization_id=device.organization_id,
                                title=f"Device Recovered: {device.name}",
                                message=f"Device '{device.name}' connectivity has been restored.",
                                severity="info",
                                category="device",
                                fingerprint=f"dev_recovered_notif:{device.id}:{int(now.timestamp())}",
                                data={"device_id": device.id},
                            ),
                        )

            device.consecutive_failures = 0
            device.last_seen = now

        db.add(device)
        await db.commit()
        return incident_result
