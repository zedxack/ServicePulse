"""
ServicePulse - Historical Uptime & Outage Duration Service
Calculates empirical downtime durations, maintenance exclusions, and historical availability.
Strictly distinguishes discrete probe ratios from duration-integrated uptime.
Performs exact interval intersections and merges overlapping maintenance windows.
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
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


def merge_intervals(intervals: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime]]:
    """
    Merge overlapping or contiguous time intervals.
    Intervals must be pairs of UTC datetimes (start, end) with start <= end.
    """
    if not intervals:
        return []

    # Sort primarily by start time, secondarily by end time
    sorted_intervals = sorted(intervals, key=lambda x: (x[0], x[1]))
    merged: List[Tuple[datetime, datetime]] = []

    for start, end in sorted_intervals:
        if not merged:
            merged.append((start, end))
        else:
            prev_start, prev_end = merged[-1]
            if start <= prev_end:
                # Overlap or contiguous -> extend boundary
                merged[-1] = (prev_start, max(prev_end, end))
            else:
                merged.append((start, end))

    return merged


def calculate_interval_intersection_duration(
    target_start: datetime,
    target_end: datetime,
    windows: List[Tuple[datetime, datetime]]
) -> float:
    """
    Calculate total overlapping seconds between [target_start, target_end]
    and a list of window intervals, merging overlapping windows first to avoid double counting.
    """
    if target_start >= target_end or not windows:
        return 0.0

    # 1. Intersect each window with target interval
    intersections: List[Tuple[datetime, datetime]] = []
    for w_start, w_end in windows:
        inter_start = max(target_start, w_start)
        inter_end = min(target_end, w_end)
        if inter_start < inter_end:
            intersections.append((inter_start, inter_end))

    if not intersections:
        return 0.0

    # 2. Merge overlapping intersections to avoid double-counting
    merged = merge_intervals(intersections)

    # 3. Sum up the merged duration
    return max(0.0, sum((end - start).total_seconds() for start, end in merged))


class UptimeService:
    """
    Computes duration-based historical uptime from verified OutageIntervals,
    accounting for scheduled maintenance windows and unobserved intervals.
    """

    @staticmethod
    def calculate_unplanned_outage_downtime(
        outage_start: datetime,
        outage_end: Optional[datetime],
        is_planned: bool,
        maintenance_windows: List[Tuple[datetime, datetime]],
        window_start: datetime,
        window_end: datetime,
    ) -> Tuple[float, float, float]:
        """
        Calculates:
        - clipped_outage_seconds
        - overlapping_maintenance_seconds
        - unplanned_downtime_seconds
        Preserving observation window boundaries and merging overlapping maintenance windows.
        """
        if is_planned:
            return 0.0, 0.0, 0.0

        o_start = _ensure_utc(outage_start)
        o_end = _ensure_utc(outage_end) or window_end

        # Clip to observation window boundaries
        clipped_start = max(o_start, window_start)
        clipped_end = min(o_end, window_end)

        if clipped_start >= clipped_end:
            return 0.0, 0.0, 0.0

        outage_duration = (clipped_end - clipped_start).total_seconds()

        # Normalize maintenance windows to UTC
        normalized_windows = [
            (_ensure_utc(ws), _ensure_utc(we))
            for ws, we in maintenance_windows
            if _ensure_utc(ws) < _ensure_utc(we)
        ]

        maint_duration = calculate_interval_intersection_duration(
            target_start=clipped_start,
            target_end=clipped_end,
            windows=normalized_windows,
        )

        unplanned = max(0.0, outage_duration - maint_duration)
        return outage_duration, maint_duration, unplanned

    @staticmethod
    async def get_organization_downtime_summary(
        org_id: int,
        window_days: int = 30,
        only_production: bool = False,
        db: AsyncSession = None
    ) -> Dict[str, Optional[float]]:
        """
        Calculates verified downtime duration in minutes over an observation window.
        Excludes scheduled maintenance periods.
        In production mode (or when only_production=True), simulated sample devices are excluded.
        """
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=window_days)
        total_window_seconds = window_days * 24 * 3600

        # Query devices for this organization
        dev_filter = [Device.organization_id == org_id, Device.is_monitored.is_(True)]
        if only_production or settings.ENVIRONMENT == "production":
            dev_filter.append(Device.is_sample_data.is_(False))

        dev_count_q = select(func.count(Device.id)).where(*dev_filter)
        total_devices = (await db.execute(dev_count_q)).scalar() or 0

        if total_devices == 0:
            return {
                "total_monitored_devices": 0,
                "observation_window_days": window_days,
                "total_downtime_minutes": 0.0,
                "measured_uptime_percent": None,
                "uptime_status": "insufficient_data",
                "total_observations": 0,
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
            if out.is_planned:
                continue

            # Find maintenance windows applicable to this device
            device_maint: List[Tuple[datetime, datetime]] = []
            for m in maintenance_windows:
                if m.device_id is None or m.device_id == out.device_id:
                    device_maint.append((m.start_time, m.end_time))

            _, _, unplanned_seconds = UptimeService.calculate_unplanned_outage_downtime(
                outage_start=out.started_at,
                outage_end=out.ended_at,
                is_planned=out.is_planned,
                maintenance_windows=device_maint,
                window_start=window_start,
                window_end=now,
            )
            total_downtime_seconds += unplanned_seconds

        total_possible_device_seconds = total_devices * total_window_seconds

        # Check total number of probe observations
        probe_count_q = select(func.count(NetworkCheck.id)).join(
            Device, NetworkCheck.device_id == Device.id
        ).where(
            Device.organization_id == org_id,
            NetworkCheck.checked_at >= window_start
        )
        if only_production or settings.ENVIRONMENT == "production":
            probe_count_q = probe_count_q.where(Device.is_sample_data.is_(False))

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
