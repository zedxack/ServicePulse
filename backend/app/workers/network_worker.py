"""
ServicePulse - Network Monitoring Worker
Standalone background daemon process for network probes, incident processing,
and automated remediation coordination.
Author: Muhammadyusuf Usmonov
"""
import asyncio
import signal

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.inventory import Device
from backend.app.models.monitoring import DeviceMonitoringConfig
from backend.app.workers.incident_processor import NetworkIncidentProcessor
from backend.app.workers.probe_engine import ProbeEngine
from backend.app.workers.remediation_worker import RemediationWorker
from backend.app.workers.scheduler import MonitoringScheduler


class NetworkWorker:
    """
    Independent network monitoring worker process.
    Orchestrates probe scheduling, execution, and incident integration.
    """

    def __init__(self):
        self.scheduler = MonitoringScheduler(concurrency_limit=settings.MONITORING_CONCURRENCY_LIMIT)
        self.is_running = False
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        """Signal the worker to stop gracefully."""
        logger.info("Stopping Network Monitoring Worker gracefully...")
        self.is_running = False
        self._stop_event.set()

    async def run_single_probe(self, device: Device, config: DeviceMonitoringConfig) -> None:
        """Execute a single probe round for a device using semaphore concurrency control."""
        acquired = await self.scheduler.acquire_device(device.id)
        if not acquired:
            # Another task is currently probing this device
            return

        async with self.scheduler.semaphore:
            try:
                # 1. Determine check type and ports
                check_type = "icmp_ping" if config.ping_enabled else "tcp_port"
                target_port = None
                if check_type == "tcp_port" and config.tcp_ports:
                    ports = [int(p.strip()) for p in config.tcp_ports.split(",") if p.strip().isdigit()]
                    target_port = ports[0] if ports else 80

                # 2. Execute Probe
                probe_res = await ProbeEngine.probe_device(
                    device_id=device.id,
                    ip_address=device.ip_address,
                    check_type=check_type,
                    port=target_port,
                    timeout_seconds=config.timeout_seconds,
                    use_simulation=config.simulation_mode or device.is_sample_data,
                )

                # 3. Process Result in an isolated database session
                async with AsyncSessionLocal() as db:
                    # Re-query device and config in this session
                    dev = await db.get(Device, device.id)
                    cfg = await db.get(DeviceMonitoringConfig, config.id)
                    if dev and cfg:
                        await NetworkIncidentProcessor.process_probe_result(
                            probe_result=probe_res,
                            device=dev,
                            config=cfg,
                            db=db,
                        )

            except Exception as e:
                logger.error("Error executing probe for device %s (%s): %s", device.name, device.ip_address, str(e))
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

    async def start(self) -> None:
        """Main worker execution loop."""
        self.is_running = True
        logger.info(
            "ServicePulse Network Monitoring Worker started. Interval: %ds, Concurrency: %d",
            settings.MONITORING_INTERVAL_SECONDS,
            settings.MONITORING_CONCURRENCY_LIMIT,
        )

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
        logger.info("ServicePulse Network Monitoring Worker shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
