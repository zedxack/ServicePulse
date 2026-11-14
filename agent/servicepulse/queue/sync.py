"""
ServicePulse Native Windows Agent - Offline Queue Synchronization Engine
Flushes buffered telemetry records to the backend with exponential backoff.
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
import random
import time
from typing import Optional

from servicepulse.api_client import AgentApiError, AgentAuthError, AgentConnectionError, ApiClient
from servicepulse.logging.setup import get_logger
from servicepulse.queue.storage import QueueStorage

logger = get_logger()


class QueueSyncWorker:
    """
    Manages delivery of queued offline telemetry records to the backend API.
    Uses exponential backoff with jitter on network failures.
    """

    def __init__(
        self,
        storage: QueueStorage,
        api_client: ApiClient,
        base_backoff_seconds: float = 2.0,
        max_backoff_seconds: float = 60.0,
        batch_size: int = 50,
    ):
        self.storage = storage
        self.api_client = api_client
        self.base_backoff = base_backoff_seconds
        self.max_backoff = max_backoff_seconds
        self.batch_size = batch_size
        self._current_backoff = base_backoff_seconds
        self._consecutive_failures = 0
        self._last_attempt_time = 0.0

    def sync_pending(self, limit: Optional[int] = None) -> int:
        """
        Synchronize a batch of pending telemetry records.
        Returns the number of successfully delivered records.
        """
        max_items = limit or self.batch_size
        pending_records = self.storage.get_pending(limit=max_items)
        if not pending_records:
            return 0

        delivered_count = 0
        for record in pending_records:
            try:
                # Ensure idempotency key is preserved
                payload = dict(record.payload)
                payload["idempotency_key"] = record.idempotency_key

                resp = self.api_client.submit_telemetry(payload)
                self.storage.mark_delivered(record.event_uuid)
                delivered_count += 1
                logger.debug(f"Delivered queued event {record.event_uuid} (server: {resp.get('status')})")

                # Reset backoff upon successful delivery
                self._current_backoff = self.base_backoff
                self._consecutive_failures = 0

            except AgentConnectionError as ce:
                # Backend unavailable -> back off and stop processing current batch
                self._record_failure(record.event_uuid, str(ce))
                logger.debug(f"Backend unreachable during queue sync: {ce}. Backing off.")
                break
            except AgentAuthError as ae:
                self._record_failure(record.event_uuid, f"Auth error: {ae}")
                logger.error(f"Authentication failure during queue sync: {ae}")
                break
            except AgentApiError as api_err:
                # Non-connection API error (e.g. 422 schema validation) -> record error and continue to next item
                self._record_failure(record.event_uuid, f"API error {api_err.status_code}: {api_err}")
                logger.warning(f"Failed to submit queued event {record.event_uuid}: {api_err}")

        return delivered_count

    def _record_failure(self, event_uuid: str, error_msg: str) -> None:
        """Update retry metadata and advance exponential backoff."""
        self.storage.record_failure(event_uuid, error_msg)
        self._consecutive_failures += 1
        jitter = random.uniform(0.8, 1.2)
        self._current_backoff = min(
            self.max_backoff,
            self.base_backoff * (2 ** min(self._consecutive_failures, 6))
        ) * jitter
        self._last_attempt_time = time.time()

    def can_attempt_sync(self) -> bool:
        """Check whether enough backoff time has elapsed to attempt another sync."""
        if self._consecutive_failures == 0:
            return True
        return (time.time() - self._last_attempt_time) >= self._current_backoff
