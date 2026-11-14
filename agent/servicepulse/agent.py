"""
ServicePulse Native Windows Agent - Core Orchestrator
Coordinates heartbeats, telemetry collection, offline queue synchronization, and command dispatching.
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
import threading
import time
from typing import Optional

from servicepulse import __version__
from servicepulse.api_client import (
    AgentAuthError,
    AgentConnectionError,
    ApiClient,
)
from servicepulse.authentication import AgentCredentials, CredentialStore
from servicepulse.collectors.network import NetworkCollector
from servicepulse.commands.dispatcher import CommandDispatcher
from servicepulse.config import AgentConfig
from servicepulse.logging.setup import get_logger
from servicepulse.queue.storage import QueueStorage
from servicepulse.queue.sync import QueueSyncWorker
from servicepulse.telemetry import TelemetryAggregator

logger = get_logger()


class ServicePulseAgent:
    """
    Main monitoring agent service that operates in both Console and Windows Service modes.
    """

    def __init__(self, config: Optional[AgentConfig] = None, simulation_mode: bool = False):
        self.config = config or AgentConfig.load()
        self.simulation_mode = simulation_mode
        self._running = False
        self._stop_event = threading.Event()

        # Initialize storage and credential vault
        self.cred_store = CredentialStore(self.config.get_credentials_path())
        self.credentials: Optional[AgentCredentials] = self.cred_store.load_credentials()

        self.api_client = ApiClient(self.config, self.credentials)
        self.queue_storage = QueueStorage(self.config.get_queue_db_path())
        self.sync_worker = QueueSyncWorker(self.queue_storage, self.api_client)
        self.command_dispatcher = CommandDispatcher(self.api_client, simulation_mode=self.simulation_mode)

        # Timers
        self._last_heartbeat = 0.0
        self._last_telemetry = 0.0
        self._last_command_poll = 0.0

    def is_enrolled(self) -> bool:
        """Check if agent has loaded credentials."""
        return self.credentials is not None and bool(self.credentials.api_token)

    def reload_credentials(self) -> bool:
        """Reload credentials from DPAPI vault."""
        self.credentials = self.cred_store.load_credentials()
        if self.credentials:
            self.api_client.set_credentials(self.credentials)
            return True
        return False

    def step(self) -> None:
        """
        Execute a single operational step across all agent subsystems:
        1. Keepalive Heartbeat
        2. Offline Queue Sync
        3. System Telemetry Gathering & Enqueueing
        4. Command Polling & Execution
        """
        now = time.time()

        if not self.is_enrolled():
            if not self.reload_credentials():
                logger.warning("Agent is not enrolled. Please enroll the agent before starting.")
                return

        # 1. Heartbeat
        if now - self._last_heartbeat >= self.config.heartbeat_interval_seconds:
            self._do_heartbeat()
            self._last_heartbeat = now

        # 2. Queue Synchronization
        if self.sync_worker.can_attempt_sync():
            delivered = self.sync_worker.sync_pending()
            if delivered > 0:
                logger.debug(f"Queue sync delivered {delivered} buffered telemetry records.")

        # 3. Telemetry Collection
        if now - self._last_telemetry >= self.config.telemetry_interval_seconds:
            self._do_telemetry_collection()
            self._last_telemetry = now

        # 4. Command Polling
        if now - self._last_command_poll >= self.config.command_poll_interval_seconds:
            self._do_command_poll()
            self._last_command_poll = now

    def _do_heartbeat(self) -> None:
        """Send keepalive heartbeat."""
        primary_ip = NetworkCollector.get_primary_ip()
        try:
            self.api_client.heartbeat(agent_version=__version__, ip_address=primary_ip)
            logger.debug("Heartbeat acknowledged by server.")
        except AgentConnectionError:
            logger.debug("Heartbeat failed: server unreachable (offline mode active).")
        except AgentAuthError as ae:
            logger.error(f"Heartbeat rejected: {ae}")
        except Exception as e:
            logger.warning(f"Unexpected heartbeat error: {e}")

    def _do_telemetry_collection(self) -> None:
        """Gathers telemetry and stores in queue, then attempts immediate sync."""
        try:
            payload = TelemetryAggregator.collect_payload()
            # Enqueue locally first (crash-resilient)
            record = self.queue_storage.enqueue(payload)
            # Enforce max record retention
            self.queue_storage.enforce_max_records(self.config.offline_queue_max_records)

            # Attempt immediate direct delivery if backoff allows
            if self.sync_worker.can_attempt_sync():
                try:
                    self.api_client.submit_telemetry(payload)
                    self.queue_storage.mark_delivered(record.event_uuid)
                    logger.info("System telemetry collected and successfully delivered.")
                except AgentConnectionError:
                    logger.info("Telemetry recorded locally in offline SQLite queue (server offline).")
                except Exception as e:
                    logger.warning(f"Failed direct telemetry submission: {e}. Buffered in queue.")
            else:
                logger.info("Telemetry buffered in offline queue (backoff active).")
        except Exception as e:
            logger.error(f"Error during telemetry collection cycle: {e}")

    def _do_command_poll(self) -> None:
        """Poll and execute pending commands."""
        try:
            processed = self.command_dispatcher.poll_and_process_commands()
            if processed > 0:
                logger.info(f"Processed {processed} remediation command(s).")
        except AgentConnectionError:
            logger.debug("Command poll skipped: server unreachable.")
        except Exception as e:
            logger.warning(f"Error during command polling: {e}")

    def run(self, stop_event: Optional[threading.Event] = None) -> None:
        """
        Run the main agent event loop continuously until stopped.
        """
        self._running = True
        actual_stop_event = stop_event or self._stop_event

        logger.info(
            f"ServicePulse Agent starting (PID {threading.get_native_id() if hasattr(threading, 'get_native_id') else 'N/A'}). "
            f"Server: {self.config.server_url}, Agent: {self.config.agent_name}"
        )

        while not actual_stop_event.is_set():
            try:
                self.step()
            except Exception as e:
                logger.error(f"Unhandled exception in agent cycle: {e}", exc_info=True)

            # Sleep short slice to be responsive to stop signals
            for _ in range(10):
                if actual_stop_event.is_set():
                    break
                time.sleep(0.1)

        self._running = False
        logger.info("ServicePulse Agent shutdown complete.")

    def stop(self) -> None:
        """Signal the agent event loop to terminate cleanly."""
        self._stop_event.set()
