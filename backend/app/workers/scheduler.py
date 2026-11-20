"""
ServicePulse - Network Monitoring Scheduler
Selects authorized targets from active organizations, prevents overlapping checks,
and orchestrates bounded asynchronous probe dispatch.
Author: Muhammadyusuf Usmonov
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.inventory import Device
from backend.app.models.monitoring import DeviceMonitoringConfig
from backend.app.models.network import NetworkCheck
from backend.app.models.organization import Organization


class MonitoringScheduler:
    """
    Manages scheduling, concurrency, target authorization, and overlap prevention.
    """

    def __init__(self, concurrency_limit: int = 10):
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self._in_flight_device_ids: Set[int] = set()
        self._lock = asyncio.Lock()

    async def acquire_device(self, device_id: int) -> bool:
        """Attempt to acquire a device for monitoring. Returns False if already in-flight."""
        async with self._lock:
            if device_id in self._in_flight_device_ids:
                return False
            self._in_flight_device_ids.add(device_id)
            return True

    async def release_device(self, device_id: int) -> None:
        """Release device after check is complete."""
        async with self._lock:
            self._in_flight_device_ids.discard(device_id)

    @staticmethod
    async def get_due_devices(db: AsyncSession) -> List[Tuple[Device, DeviceMonitoringConfig]]:
        """
        Query devices eligible and due for network checks:
        1. Organization is active.
        2. Device is_monitored is True.
        3. Monitoring config exists, is_enabled is True, and is_authorized is True.
        4. Not currently checked within the configured interval.
        """
        now = datetime.now(timezone.utc)

        # Query devices belonging to active orgs with active monitoring config
        query = (
            select(Device, DeviceMonitoringConfig)
            .join(Organization, Device.organization_id == Organization.id)
            .outerjoin(DeviceMonitoringConfig, Device.id == DeviceMonitoringConfig.device_id)
            .where(
                Organization.is_active.is_(True),
                Device.is_monitored.is_(True),
            )
        )
        results = (await db.execute(query)).all()

        due_list: List[Tuple[Device, DeviceMonitoringConfig]] = []
        for dev, cfg in results:
            # If no explicit config exists, create default on the fly
            if cfg is None:
                cfg = DeviceMonitoringConfig(
                    device_id=dev.id,
                    is_enabled=True,
                    is_authorized=True,
                    ping_enabled=True,
                    tcp_ports="80,443",
                    check_interval_seconds=settings.MONITORING_INTERVAL_SECONDS,
                    timeout_seconds=float(settings.PING_TIMEOUT_SECONDS),
                    consecutive_failure_threshold=settings.CONSECUTIVE_FAILURE_THRESHOLD,
                    simulation_mode=dev.is_sample_data,
                )
                db.add(cfg)
                await db.flush()

            # Security Check: Reject unauthorized or disabled configurations
            if not cfg.is_enabled or not cfg.is_authorized:
                continue

            # Check if device is due based on interval
            interval = timedelta(seconds=cfg.check_interval_seconds)
            # Find timestamp of most recent check
            latest_check_q = (
                select(NetworkCheck.checked_at)
                .where(NetworkCheck.device_id == dev.id)
                .order_by(NetworkCheck.checked_at.desc())
                .limit(1)
            )
            last_checked = (await db.execute(latest_check_q)).scalar_one_or_none()

            if last_checked is None or (now - last_checked) >= interval:
                due_list.append((dev, cfg))

        return due_list
