"""
ServicePulse - Historical Uptime & Outage Duration Service
Calculates empirical downtime durations, maintenance exclusions, and historical availability.
Strictly distinguishes discrete probe ratios from duration-integrated uptime.
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.inventory import Device
from backend.app.models.monitoring import (
    MaintenanceWindow,
    OutageInterval,
)
from backend.app.models.network import NetworkCheck


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class UptimeService:
    """
    Computes duration-based historical uptime from verified OutageIntervals,
    accounting for scheduled maintenance windows and unobserved intervals.
    """

    @staticmethod
    async def get_organization_downtime_summary(
        org_id: int,
        window_days: int = 30,
        db: AsyncSession = None
    ) -> Dict[str, Optional[float]]:
        """
        Calculates verified downtime duration in minutes over an observation window.
        Excludes scheduled maintenance periods.
        """
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=window_days)
        total_window_seconds = window_days * 24 * 3600

        # Query all devices for this organization
        dev_count_q = select(func.count(Device.id)).where(
            Device.organization_id == org_id,
            Device.is_monitored.is_(True)
        )
        total_devices = (await db.execute(dev_count_q)).scalar() or 0

        if total_devices == 0:
            return {
                "total_monitored_devices": 0,
                "observation_window_days": window_days,
                "total_downtime_minutes": 0.0,
                "measured_uptime_percent": None,
                "uptime_status": "insufficient_data",
            }

        # Query confirmed OutageIntervals overlapping the observation window
        outages_q = select(OutageInterval).where(
            OutageInterval.organization_id == org_id,
            OutageInterval.started_at <= now,
            or_(
                OutageInterval.ended_at.is_(None),
                OutageInterval.ended_at >= window_start,
            )
        )
        outages = list((await db.execute(outages_q)).scalars().all())

        # Query maintenance windows to exclude planned downtime
        maint_q = select(MaintenanceWindow).where(
            MaintenanceWindow.organization_id == org_id,
            MaintenanceWindow.is_active.is_(True),
            MaintenanceWindow.start_time <= now,
            MaintenanceWindow.end_time >= window_start,
        )
        maintenance_windows = list((await db.execute(maint_q)).scalars().all())

        total_downtime_seconds = 0.0
        for out in outages:
            out_start = _ensure_utc(out.started_at)
            out_end = _ensure_utc(out.ended_at) or now
            # Clip outage start and end to the observation window
            o_start = max(out_start, window_start)
            o_end = min(out_end, now)
            duration = max(0.0, (o_end - o_start).total_seconds())

            # Check if this outage overlaps with an approved maintenance window
            is_under_maint = False
            for m in maintenance_windows:
                m_start = _ensure_utc(m.start_time)
                m_end = _ensure_utc(m.end_time)
                if (m.device_id is None or m.device_id == out.device_id):
                    if m_start <= o_start and m_end >= o_end:
                        is_under_maint = True
                        break

            if not is_under_maint and not out.is_planned:
                total_downtime_seconds += duration

        total_possible_device_seconds = total_devices * total_window_seconds

        # Check total number of probe observations
        probe_count_q = select(func.count(NetworkCheck.id)).join(
            Device, NetworkCheck.device_id == Device.id
        ).where(
            Device.organization_id == org_id,
            NetworkCheck.checked_at >= window_start
        )
        total_probes = (await db.execute(probe_count_q)).scalar() or 0

        # Minimum required observations per device: 10
        min_required_probes = total_devices * 10
        if total_probes < min_required_probes:
            # Insufficient continuous observation data
            return {
                "total_monitored_devices": total_devices,
                "observation_window_days": window_days,
                "total_downtime_minutes": round(total_downtime_seconds / 60.0, 1),
                "measured_uptime_percent": None,
                "uptime_status": "insufficient_data",
                "total_observations": total_probes,
            }

        # Calculate continuous time-integrated uptime percent
        total_uptime_seconds = max(0.0, total_possible_device_seconds - total_downtime_seconds)
        measured_uptime = round((total_uptime_seconds / total_possible_device_seconds) * 100.0, 2)

        return {
            "total_monitored_devices": total_devices,
            "observation_window_days": window_days,
            "total_downtime_minutes": round(total_downtime_seconds / 60.0, 1),
            "measured_uptime_percent": measured_uptime,
            "uptime_status": "operational",
            "total_observations": total_probes,
        }
