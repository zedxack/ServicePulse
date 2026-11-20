"""
ServicePulse - Network Monitoring Service
Business logic for querying network checks, device statuses, on-demand probes, and maintenance windows.
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.models.inventory import Device
from backend.app.models.monitoring import (
    DeviceMonitoringConfig,
    MaintenanceWindow,
    OutageInterval,
)
from backend.app.models.network import NetworkCheck
from backend.app.models.user import User
from backend.app.schemas.monitoring import (
    DeviceMonitoringConfigRead,
    DeviceStatusResponse,
    MaintenanceWindowCreate,
    NetworkHealthResponse,
    ProbeRequest,
    ProbeResult,
)
from backend.app.workers.incident_processor import NetworkIncidentProcessor
from backend.app.workers.probe_engine import ProbeEngine


class NetworkService:
    @staticmethod
    async def list_checks(
        skip: int,
        limit: int,
        device_id: Optional[int],
        check_type: Optional[str],
        is_successful: Optional[bool],
        scoped_org_id: Optional[int],
        db: AsyncSession
    ) -> List[NetworkCheck]:
        """List network checks with filtering and tenant isolation."""
        q = select(NetworkCheck).join(Device, NetworkCheck.device_id == Device.id)
        if scoped_org_id is not None:
            q = q.where(Device.organization_id == scoped_org_id)
        if device_id is not None:
            q = q.where(NetworkCheck.device_id == device_id)
        if check_type is not None:
            q = q.where(NetworkCheck.check_type == check_type)
        if is_successful is not None:
            q = q.where(NetworkCheck.is_successful == is_successful)

        q = q.order_by(NetworkCheck.checked_at.desc()).offset(skip).limit(limit)
        return list((await db.execute(q)).scalars().all())

    @staticmethod
    async def get_device_checks(
        device_id: int,
        skip: int,
        limit: int,
        scoped_org_id: Optional[int],
        db: AsyncSession
    ) -> List[NetworkCheck]:
        """Get network checks for a specific device, enforcing tenant ownership."""
        dev = await db.get(Device, device_id)
        if not dev or (scoped_org_id is not None and dev.organization_id != scoped_org_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found in your organization")

        q = (
            select(NetworkCheck)
            .where(NetworkCheck.device_id == device_id)
            .order_by(NetworkCheck.checked_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list((await db.execute(q)).scalars().all())

    @staticmethod
    async def trigger_on_demand_probe(
        device_id: int,
        probe_req: ProbeRequest,
        scoped_org_id: Optional[int],
        db: AsyncSession
    ) -> ProbeResult:
        """Trigger an immediate on-demand probe for an authorized device."""
        q = (
            select(Device)
            .options(selectinload(Device.monitoring_config))
            .where(Device.id == device_id)
        )
        dev = (await db.execute(q)).scalar_one_or_none()
        if not dev or (scoped_org_id is not None and dev.organization_id != scoped_org_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found in your organization")

        cfg = dev.monitoring_config
        if not cfg:
            cfg = DeviceMonitoringConfig(
                device_id=dev.id,
                is_enabled=True,
                is_authorized=True,
                ping_enabled=True,
                tcp_ports="80,443",
                check_interval_seconds=30,
                timeout_seconds=3.0,
                consecutive_failure_threshold=3,
                simulation_mode=dev.is_sample_data,
            )
            db.add(cfg)
            await db.flush()

        if not cfg.is_authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Network monitoring is not authorized for this device by platform policy"
            )

        # Execute Probe
        # Safety rule: Real devices (is_sample_data=False) must NEVER enter simulation mode.
        use_sim = False if (not dev.is_sample_data or settings.ENVIRONMENT == "production") else bool(cfg.simulation_mode)

        probe_res = await ProbeEngine.probe_device(
            device_id=dev.id,
            ip_address=dev.ip_address,
            check_type=probe_req.check_type,
            port=probe_req.port,
            timeout_seconds=cfg.timeout_seconds,
            use_simulation=use_sim,
        )

        # Process Result through incident engine
        await NetworkIncidentProcessor.process_probe_result(
            probe_result=probe_res,
            device=dev,
            config=cfg,
            db=db,
        )
        return probe_res

    @staticmethod
    async def get_device_status(
        device_id: int,
        scoped_org_id: Optional[int],
        db: AsyncSession
    ) -> DeviceStatusResponse:
        """Retrieve real-time monitoring and outage status for a device."""
        q = (
            select(Device)
            .options(selectinload(Device.monitoring_config))
            .where(Device.id == device_id)
        )
        dev = (await db.execute(q)).scalar_one_or_none()
        if not dev or (scoped_org_id is not None and dev.organization_id != scoped_org_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found in your organization")

        # Check last attempted and last successful check
        attempt_q = (
            select(NetworkCheck.checked_at)
            .where(NetworkCheck.device_id == device_id)
            .order_by(NetworkCheck.checked_at.desc())
            .limit(1)
        )
        last_attempt = (await db.execute(attempt_q)).scalar_one_or_none()

        success_q = (
            select(NetworkCheck.checked_at)
            .where(NetworkCheck.device_id == device_id, NetworkCheck.is_successful.is_(True))
            .order_by(NetworkCheck.checked_at.desc())
            .limit(1)
        )
        last_success = (await db.execute(success_q)).scalar_one_or_none()

        # Check active outage
        outage_q = select(func.count(OutageInterval.id)).where(
            OutageInterval.device_id == device_id,
            OutageInterval.ended_at.is_(None)
        )
        active_outage = ((await db.execute(outage_q)).scalar() or 0) > 0

        cfg_read = None
        if dev.monitoring_config:
            cfg_read = DeviceMonitoringConfigRead.model_validate(dev.monitoring_config)

        return DeviceStatusResponse(
            device_id=dev.id,
            organization_id=dev.organization_id,
            name=dev.name,
            hostname=dev.hostname,
            ip_address=dev.ip_address,
            device_type=dev.device_type,
            status=dev.status,
            consecutive_failures=dev.consecutive_failures,
            last_seen=dev.last_seen,
            last_attempted_check=last_attempt,
            last_successful_check=last_success,
            is_monitored=dev.is_monitored,
            is_authorized=dev.monitoring_config.is_authorized if dev.monitoring_config else True,
            active_outage=active_outage,
            monitoring_config=cfg_read,
        )

    @staticmethod
    async def get_network_health(
        scoped_org_id: Optional[int],
        db: AsyncSession
    ) -> NetworkHealthResponse:
        """Aggregate health statistics for the monitoring subsystem."""
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        dev_q = select(func.count(Device.id)).where(Device.is_monitored.is_(True))
        checks_q = select(func.count(NetworkCheck.id)).join(Device, NetworkCheck.device_id == Device.id)
        recent_fail_q = (
            select(func.count(NetworkCheck.id))
            .join(Device, NetworkCheck.device_id == Device.id)
            .where(NetworkCheck.is_successful.is_(False), NetworkCheck.checked_at >= one_hour_ago)
        )
        outages_q = (
            select(func.count(OutageInterval.id))
            .where(OutageInterval.ended_at.is_(None))
        )

        if scoped_org_id is not None:
            dev_q = dev_q.where(Device.organization_id == scoped_org_id)
            checks_q = checks_q.where(Device.organization_id == scoped_org_id)
            recent_fail_q = recent_fail_q.where(Device.organization_id == scoped_org_id)
            outages_q = outages_q.where(OutageInterval.organization_id == scoped_org_id)

        active_devs = (await db.execute(dev_q)).scalar() or 0
        total_checks = (await db.execute(checks_q)).scalar() or 0
        recent_fails = (await db.execute(recent_fail_q)).scalar() or 0
        active_outages = (await db.execute(outages_q)).scalar() or 0

        return NetworkHealthResponse(
            worker_status="operational",
            active_monitored_devices=active_devs,
            total_probes_recorded=total_checks,
            recent_failures_count=recent_fails,
            active_outages_count=active_outages,
            timestamp=now,
        )

    @staticmethod
    async def create_maintenance_window(
        m_in: MaintenanceWindowCreate,
        user: User,
        scoped_org_id: Optional[int],
        db: AsyncSession
    ) -> MaintenanceWindow:
        """Create a scheduled maintenance window for an organization or specific device."""
        target_org = scoped_org_id or user.organization_id
        if not target_org:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Organization ID required")

        if m_in.device_id:
            dev = await db.get(Device, m_in.device_id)
            if not dev or (scoped_org_id is not None and dev.organization_id != scoped_org_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target device not found in your organization")

        window = MaintenanceWindow(
            organization_id=target_org,
            title=m_in.title.strip(),
            description=m_in.description,
            device_id=m_in.device_id,
            start_time=m_in.start_time,
            end_time=m_in.end_time,
            is_active=True,
            created_by_user_id=user.id,
        )
        db.add(window)
        await db.commit()
        await db.refresh(window)
        return window

    @staticmethod
    async def list_maintenance_windows(
        scoped_org_id: Optional[int],
        db: AsyncSession
    ) -> List[MaintenanceWindow]:
        """List active/scheduled maintenance windows."""
        q = select(MaintenanceWindow).order_by(MaintenanceWindow.start_time.desc())
        if scoped_org_id is not None:
            q = q.where(MaintenanceWindow.organization_id == scoped_org_id)
        return list((await db.execute(q)).scalars().all())
