"""
ServicePulse - Network Monitoring Worker
Standalone background daemon process for network probes, incident processing,
and automated remediation coordination.
Author: Muhammadyusuf Usmonov
"""
import asyncio
import signal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.inventory import Device
from backend.app.models.monitoring import DeviceMonitoringConfig
from backend.app.schemas.monitoring import ProbeResult
from backend.app.workers.incident_processor import NetworkIncidentProcessor
from backend.app.workers.lease_manager import WorkerLeaseManager
from backend.app.workers.probe_engine import ProbeEngine
from backend.app.workers.remediation_worker import RemediationWorker
from backend.app.workers.scheduler import MonitoringScheduler


class NetworkWorker:
    """
    Independent network monitoring worker process.
    Orchestrates probe scheduling, execution, and incident integration.
    Acquires database-backed singleton leadership before monitoring.
    """

    def __init__(self, lease_manager: Optional[WorkerLeaseManager] = None):
        self.scheduler = MonitoringScheduler(concurrency_limit=settings.MONITORING_CONCURRENCY_LIMIT)
        self.is_running = False
        self._stop_event = asyncio.Event()
        self.lease_manager = lease_manager or WorkerLeaseManager()

    def stop(self) -> None:
        """Signal the worker to stop gracefully."""
        logger.info("Stopping Network Monitoring Worker gracefully...")
        self.is_running = False
        self._stop_event.set()

    async def stop_and_release(self) -> None:
        """Signal worker to stop and immediately release database lease."""
        self.stop()
        await self.lease_manager.release_lease()

    async def run_single_probe(
        self,
        device: Device,
        config: DeviceMonitoringConfig,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ProbeResult]:
        """Execute a single probe round for a device using semaphore concurrency control."""
        acquired = await self.scheduler.acquire_device(device.id)
        if not acquired:
            # Another task is currently probing this device
            return None

        async with self.scheduler.semaphore:
            try:
                # 1. Determine check type and ports
                check_type = "icmp_ping" if config.ping_enabled else "tcp_port"
                target_port = None
                if check_type == "tcp_port" and config.tcp_ports:
                    ports = [int(p.strip()) for p in config.tcp_ports.split(",") if p.strip().isdigit()]
                    target_port = ports[0] if ports else 80

                # 2. Execute Probe
                # Safety rule: Real devices (is_sample_data=False) must NEVER silently enter simulation.
                # Simulation is strictly reserved for explicitly marked sample devices (is_sample_data=True).
                if not device.is_sample_data or settings.ENVIRONMENT == "production":
                    use_simulation = False
                else:
                    use_simulation = bool(config.simulation_mode or settings.WORKER_SIMULATION_MODE)

                probe_res = await ProbeEngine.probe_device(
                    device_id=device.id,
                    ip_address=device.ip_address,
                    check_type=check_type,
                    port=target_port,
                    timeout_seconds=config.timeout_seconds,
                    use_simulation=use_simulation,
                )

                # 3. Process Result in database session
                if db is not None:
                    await NetworkIncidentProcessor.process_probe_result(
                        probe_result=probe_res,
                        device=device,
                        config=config,
                        db=db,
                    )
                else:
                    async with AsyncSessionLocal() as session:
                        dev = await session.get(Device, device.id)
                        cfg = await session.get(DeviceMonitoringConfig, config.id)
                        if dev and cfg:
                            await NetworkIncidentProcessor.process_probe_result(
                                probe_result=probe_res,
                                device=dev,
                                config=cfg,
                                db=session,
                            )

                return probe_res

            except Exception as e:
                logger.error("Error executing probe for device %s (%s): %s", device.name, device.ip_address, str(e))
                return None
            finally:
                await self.scheduler.release_device(device.id)

    async def run_cycle(self) -> int:
        """Execute one complete monitoring and remediation cycle."""
        async with AsyncSessionLocal() as db:
            due_items = await self.scheduler.get_due_devices(db)
            # Process pending remediation commands
            await RemediationWorker.process_pending_commands(db)

        if not due_items:
            return 0

        logger.debug("Dispatching network probes for %d due devices...", len(due_items))
        tasks = [self.run_single_probe(dev, cfg) for dev, cfg in due_items]
        await asyncio.gather(*tasks, return_exceptions=True)
        return len(due_items)

    async def start(self) -> bool:
        """
        Main worker execution loop.
        Acquires database-backed singleton advisory lock before executing.
        Safely refuses leadership if another instance holds the lease.
        """
        acquired = await self.lease_manager.acquire_lease()
        if not acquired:
            logger.warning("NetworkWorker could not acquire database leadership lease. Refusing leadership and exiting.")
            self.is_running = False
            return False

        self.is_running = True
        logger.info(
            "ServicePulse Network Monitoring Worker started as leader. Interval: %ds, Concurrency: %d",
            settings.MONITORING_INTERVAL_SECONDS,
            settings.MONITORING_CONCURRENCY_LIMIT,
        )

        try:
            while self.is_running and not self._stop_event.is_set():
                t_start = asyncio.get_event_loop().time()
                try:
                    count = await self.run_cycle()
                    if count > 0:
                        logger.info("Completed monitoring cycle for %d devices.", count)
                except Exception as e:
                    logger.error("Unhandled exception in monitoring cycle: %s", str(e), exc_info=True)

                # Wait for next interval or shutdown signal
                elapsed = asyncio.get_event_loop().time() - t_start
                sleep_duration = max(1.0, float(settings.MONITORING_INTERVAL_SECONDS) - elapsed)
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=sleep_duration)
                except asyncio.TimeoutError:
                    pass
            return True
        finally:
            await self.lease_manager.release_lease()
            self.is_running = False


async def main():
    worker = NetworkWorker()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.stop)
        except NotImplementedError:
            # Windows does not support add_signal_handler for some signals
            pass

    try:
        await worker.start()
    except (asyncio.CancelledError, KeyboardInterrupt):
        worker.stop()
    finally:
        await worker.lease_manager.release_lease()
        logger.info("ServicePulse Network Monitoring Worker shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
