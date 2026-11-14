"""
ServicePulse - Analytics & SLA Service
Empirical duration-based SLA calculations, maintenance window exclusions,
trend aggregations, and data completeness verification.
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.incident import Incident
from backend.app.models.inventory import Device
from backend.app.models.monitoring import MaintenanceWindow, OutageInterval
from backend.app.models.network import NetworkCheck
from backend.app.schemas.analytics import (
    AvailabilityTrendPoint,
    AvailabilityTrendResponse,
    IncidentTrendPoint,
    IncidentTrendResponse,
    SLAOverviewResponse,
)
from backend.app.services.uptime_service import (
    _ensure_utc,
    calculate_interval_intersection_duration,
    merge_intervals,
)


class AnalyticsService:
    @staticmethod
    async def get_sla_overview(
        org_id: int,
        days: int = 30,
        device_id: Optional[int] = None,
        db: AsyncSession = None,
    ) -> SLAOverviewResponse:
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=days)
        window_seconds = days * 24 * 3600

        # 1. Monitored devices
        dev_q = select(Device).where(
            Device.organization_id == org_id,
            Device.is_monitored.is_(True),
        )
        if device_id:
            dev_q = dev_q.where(Device.id == device_id)
        if settings.ENVIRONMENT == "production":
            dev_q = dev_q.where(Device.is_sample_data.is_(False))

        devices = list((await db.execute(dev_q)).scalars().all())
        total_devices = len(devices)

        target_sla = settings.SLA_TARGET_PERCENT

        if total_devices == 0:
            return SLAOverviewResponse(
                sla_target_percent=target_sla,
                measured_uptime_percent=None,
                is_sla_met=None,
                uptime_status="insufficient_data",
                data_completeness="insufficient_data",
                observation_window_days=days,
                period_start=period_start,
                period_end=now,
                total_monitored_devices=0,
                total_downtime_minutes=0.0,
                eligible_duration_minutes=0.0,
                excluded_maintenance_minutes=0.0,
                total_outages=0,
            )

        # 2. Maintenance windows
        maint_q = select(MaintenanceWindow).where(
            MaintenanceWindow.organization_id == org_id,
            MaintenanceWindow.is_active.is_(True),
            MaintenanceWindow.start_time <= now,
            MaintenanceWindow.end_time >= period_start,
        )
        if device_id:
            maint_q = maint_q.where(
                or_(MaintenanceWindow.device_id.is_(None), MaintenanceWindow.device_id == device_id)
            )
        maintenance_windows = list((await db.execute(maint_q)).scalars().all())

        # 3. Outage intervals overlapping window
        out_q = select(OutageInterval).where(
            OutageInterval.organization_id == org_id,
            OutageInterval.started_at <= now,
            or_(OutageInterval.ended_at.is_(None), OutageInterval.ended_at >= period_start),
        )
        if device_id:
            out_q = out_q.where(OutageInterval.device_id == device_id)
        outages = list((await db.execute(out_q)).scalars().all())

        # Calculate per-device downtime and maintenance exclusion
        total_eligible_seconds = 0.0
        total_unavailable_seconds = 0.0
        total_excluded_maintenance_seconds = 0.0

        for dev in devices:
            # Device maintenance windows
            dev_maint_intervals: List[Tuple[datetime, datetime]] = []
            for m in maintenance_windows:
                if m.device_id is None or m.device_id == dev.id:
                    s = max(_ensure_utc(m.start_time), period_start)
                    e = min(_ensure_utc(m.end_time), now)
                    if s < e:
                        dev_maint_intervals.append((s, e))

            merged_maint = merge_intervals(dev_maint_intervals)
            dev_maint_dur = sum((e - s).total_seconds() for s, e in merged_maint)
            total_excluded_maintenance_seconds += dev_maint_dur

            # Eligible duration per device = window_seconds - dev_maint_dur
            dev_eligible = max(0.0, window_seconds - dev_maint_dur)
            total_eligible_seconds += dev_eligible

            # Device outages
            dev_outage_intervals: List[Tuple[datetime, datetime]] = []
            for out in outages:
                if out.device_id == dev.id and not out.is_planned:
                    s = max(_ensure_utc(out.started_at), period_start)
                    e = min(_ensure_utc(out.ended_at) or now, now)
                    if s < e:
                        dev_outage_intervals.append((s, e))

            merged_outages = merge_intervals(dev_outage_intervals)

            # For each merged outage, subtract overlapping maintenance
            for out_s, out_e in merged_outages:
                maint_overlap = calculate_interval_intersection_duration(out_s, out_e, merged_maint)
                unplanned = max(0.0, (out_e - out_s).total_seconds() - maint_overlap)
                total_unavailable_seconds += unplanned

        # 4. Check probe observations for data completeness
        probe_q = (
            select(func.count(NetworkCheck.id))
            .join(Device, NetworkCheck.device_id == Device.id)
            .where(
                Device.organization_id == org_id,
                NetworkCheck.checked_at >= period_start,
            )
        )
        if device_id:
            probe_q = probe_q.where(Device.id == device_id)
        if settings.ENVIRONMENT == "production":
            probe_q = probe_q.where(Device.is_sample_data.is_(False))

        total_probes = (await db.execute(probe_q)).scalar() or 0
        min_required_probes = total_devices * 10

        # Incidents for MTTR calculation
        inc_q = select(Incident).where(
            Incident.organization_id == org_id,
            Incident.first_seen_at >= period_start,
        )
        if device_id:
            inc_q = inc_q.where(Incident.device_id == device_id)
        incidents = list((await db.execute(inc_q)).scalars().all())

        resolved_times = [
            (inc.resolved_at - inc.first_seen_at).total_seconds() / 60.0
            for inc in incidents
            if inc.resolved_at and inc.resolved_at >= inc.first_seen_at
        ]
        mttr = round(sum(resolved_times) / len(resolved_times), 1) if resolved_times else None

        if total_probes < min_required_probes or total_eligible_seconds <= 0.0:
            return SLAOverviewResponse(
                sla_target_percent=target_sla,
                measured_uptime_percent=None,
                is_sla_met=None,
                uptime_status="insufficient_data",
                data_completeness="insufficient_data",
                observation_window_days=days,
                period_start=period_start,
                period_end=now,
                total_monitored_devices=total_devices,
                total_downtime_minutes=round(total_unavailable_seconds / 60.0, 1),
                eligible_duration_minutes=round(total_eligible_seconds / 60.0, 1),
                excluded_maintenance_minutes=round(total_excluded_maintenance_seconds / 60.0, 1),
                total_outages=len(outages),
                mttr_minutes=mttr,
            )

        # Uptime % = (Eligible Duration - Unavailable Duration) / Eligible Duration * 100
        available_seconds = max(0.0, total_eligible_seconds - total_unavailable_seconds)
        uptime_pct = round((available_seconds / total_eligible_seconds) * 100.0, 2)
        is_met = uptime_pct >= target_sla

        status_str = "operational" if is_met else "degraded"

        return SLAOverviewResponse(
            sla_target_percent=target_sla,
            measured_uptime_percent=uptime_pct,
            is_sla_met=is_met,
            uptime_status=status_str,
            data_completeness="complete",
            observation_window_days=days,
            period_start=period_start,
            period_end=now,
            total_monitored_devices=total_devices,
            total_downtime_minutes=round(total_unavailable_seconds / 60.0, 1),
            eligible_duration_minutes=round(total_eligible_seconds / 60.0, 1),
            excluded_maintenance_minutes=round(total_excluded_maintenance_seconds / 60.0, 1),
            total_outages=len(outages),
            mttr_minutes=mttr,
        )

    @staticmethod
    async def get_availability_trend(
        org_id: int,
        days: int = 14,
        device_id: Optional[int] = None,
        db: AsyncSession = None,
    ) -> AvailabilityTrendResponse:
        now = datetime.now(timezone.utc)
        points: List[AvailabilityTrendPoint] = []

        # Iterate day by day backwards
        for i in range(days - 1, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = min(day_start + timedelta(days=1), now)
            day_str = day_start.strftime("%Y-%m-%d")

            # Check if day has data
            probe_q = (
                select(func.count(NetworkCheck.id))
                .join(Device, NetworkCheck.device_id == Device.id)
                .where(
                    Device.organization_id == org_id,
                    NetworkCheck.checked_at >= day_start,
                    NetworkCheck.checked_at < day_end,
                )
            )
            if device_id:
                probe_q = probe_q.where(Device.id == device_id)
            probes = (await db.execute(probe_q)).scalar() or 0

            # Outages overlapping this day
            out_q = select(OutageInterval).where(
                OutageInterval.organization_id == org_id,
                OutageInterval.started_at < day_end,
                or_(OutageInterval.ended_at.is_(None), OutageInterval.ended_at > day_start),
            )
            if device_id:
                out_q = out_q.where(OutageInterval.device_id == device_id)
            outages = list((await db.execute(out_q)).scalars().all())

            # Sum daily downtime
            daily_outage_intervals: List[Tuple[datetime, datetime]] = []
            for out in outages:
                if not out.is_planned:
                    s = max(_ensure_utc(out.started_at), day_start)
                    e = min(_ensure_utc(out.ended_at) or now, day_end)
                    if s < e:
                        daily_outage_intervals.append((s, e))

            merged = merge_intervals(daily_outage_intervals)
            downtime_sec = sum((e - s).total_seconds() for s, e in merged)
            downtime_min = round(downtime_sec / 60.0, 1)

            day_duration_sec = (day_end - day_start).total_seconds()
            if probes < 5 or day_duration_sec <= 0:
                points.append(
                    AvailabilityTrendPoint(
                        date=day_str,
                        uptime_percent=None,
                        downtime_minutes=downtime_min,
                        is_complete=False,
                    )
                )
            else:
                uptime_pct = round(max(0.0, (day_duration_sec - downtime_sec) / day_duration_sec) * 100.0, 2)
                points.append(
                    AvailabilityTrendPoint(
                        date=day_str,
                        uptime_percent=uptime_pct,
                        downtime_minutes=downtime_min,
                        is_complete=True,
                    )
                )

        return AvailabilityTrendResponse(points=points)

    @staticmethod
    async def get_incident_trends(
        org_id: int,
        days: int = 14,
        db: AsyncSession = None,
    ) -> IncidentTrendResponse:
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=days)

        q = select(Incident).where(
            Incident.organization_id == org_id,
            Incident.first_seen_at >= period_start,
        )
        incidents = list((await db.execute(q)).scalars().all())

        # Group by date
        daily_stats: Dict[str, Dict[str, int]] = {}
        for i in range(days - 1, -1, -1):
            day_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_stats[day_str] = {"critical": 0, "warning": 0, "info": 0, "resolved": 0}

        for inc in incidents:
            d_str = inc.first_seen_at.strftime("%Y-%m-%d")
            if d_str in daily_stats:
                sev = inc.severity.lower()
                if sev in daily_stats[d_str]:
                    daily_stats[d_str][sev] += 1
                if inc.status == "resolved":
                    daily_stats[d_str]["resolved"] += 1

        points = [
            IncidentTrendPoint(
                date=k,
                critical_count=v["critical"],
                warning_count=v["warning"],
                info_count=v["info"],
                resolved_count=v["resolved"],
            )
            for k, v in sorted(daily_stats.items())
        ]

        return IncidentTrendResponse(total_incidents=len(incidents), points=points)
