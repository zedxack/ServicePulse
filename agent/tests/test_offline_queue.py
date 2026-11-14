"""
ServicePulse Windows Agent - Offline Queue Test Suite
Verifies crash-resilience, SQLite WAL persistence, FIFO delivery, corruption recovery, and exponential backoff.
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
from pathlib import Path
from unittest.mock import MagicMock

from servicepulse.api_client import AgentConnectionError
from servicepulse.queue.storage import QueueStorage
from servicepulse.queue.sync import QueueSyncWorker


def test_queue_enqueue_and_fifo_retrieval(test_queue_storage: QueueStorage):
    """Verify records are enqueued and returned in strict FIFO order."""
    payload1 = {"cpu_percent": 10.0, "ram_percent": 20.0, "idempotency_key": "k1"}
    payload2 = {"cpu_percent": 30.0, "ram_percent": 40.0, "idempotency_key": "k2"}

    rec1 = test_queue_storage.enqueue(payload1)
    rec2 = test_queue_storage.enqueue(payload2)

    pending = test_queue_storage.get_pending(limit=10)
    assert len(pending) == 2
    assert pending[0].event_uuid == rec1.event_uuid
    assert pending[1].event_uuid == rec2.event_uuid
    assert pending[0].payload["cpu_percent"] == 10.0


def test_queue_persistence_across_restarts(tmp_data_dir: Path):
    """Verify queued data survives complete agent restarts / database reopening."""
    db_path = tmp_data_dir / "restart_test_queue.db"

    # Session 1: Enqueue records
    store1 = QueueStorage(db_path)
    store1.enqueue({"metric": "first", "idempotency_key": "rst-1"})
    store1.enqueue({"metric": "second", "idempotency_key": "rst-2"})

    # Session 2: Reopen from fresh instance
    store2 = QueueStorage(db_path)
    pending = store2.get_pending(limit=10)
    assert len(pending) == 2
    assert pending[0].idempotency_key == "rst-1"
    assert pending[1].idempotency_key == "rst-2"


def test_queue_mark_delivered(test_queue_storage: QueueStorage):
    """Verify delivered items transition to 'sent' and are excluded from pending batches."""
    rec = test_queue_storage.enqueue({"val": 42, "idempotency_key": "deliv-1"})
    assert len(test_queue_storage.get_pending()) == 1

    test_queue_storage.mark_delivered(rec.event_uuid)
    assert len(test_queue_storage.get_pending()) == 0

    stats = test_queue_storage.get_stats()
    assert stats["sent"] == 1
    assert stats["pending"] == 0


def test_queue_record_failure_and_retry_increment(test_queue_storage: QueueStorage):
    """Verify failed delivery increments retry count and stores error message."""
    rec = test_queue_storage.enqueue({"val": 99, "idempotency_key": "fail-1"})

    test_queue_storage.record_failure(rec.event_uuid, "HTTP 503 Service Unavailable")
    pending = test_queue_storage.get_pending()
    assert len(pending) == 1
    assert pending[0].retry_count == 1
    assert "HTTP 503" in (pending[0].error_message or "")


def test_queue_enforce_max_records(test_queue_storage: QueueStorage):
    """Verify queue enforces size limit by pruning delivered records first, then oldest."""
    for i in range(15):
        r = test_queue_storage.enqueue({"idx": i, "idempotency_key": f"key-{i}"})
        if i < 5:
            test_queue_storage.mark_delivered(r.event_uuid)

    stats = test_queue_storage.get_stats()
    assert stats["total"] == 15

    # Enforce limit of 8 records
    pruned = test_queue_storage.enforce_max_records(max_records=8)
    assert pruned == 7
    new_stats = test_queue_storage.get_stats()
    assert new_stats["total"] == 8


def test_queue_corruption_recovery(tmp_data_dir: Path):
    """Verify corrupt database file is backed up and re-initialized without crashing."""
    db_path = tmp_data_dir / "corrupt_test.db"

    # Create invalid file content simulating filesystem corruption
    with open(db_path, "wb") as f:
        f.write(b"CORRUPTED_NON_SQLITE_GARBAGE_HEADER")

    # QueueStorage should detect corrupt file and create a fresh healthy database
    store = QueueStorage(db_path)
    rec = store.enqueue({"status": "recovered", "idempotency_key": "rec-1"})
    assert rec.id is not None
    assert len(store.get_pending()) == 1


def test_queue_sync_worker_delivery_success(test_queue_storage: QueueStorage):
    """Verify QueueSyncWorker delivers pending records via API client and marks them delivered."""
    mock_client = MagicMock()
    mock_client.submit_telemetry.return_value = {"status": "recorded"}

    test_queue_storage.enqueue({"cpu": 12.0, "idempotency_key": "sync-1"})
    test_queue_storage.enqueue({"cpu": 15.0, "idempotency_key": "sync-2"})

    worker = QueueSyncWorker(test_queue_storage, mock_client)
    delivered = worker.sync_pending()

    assert delivered == 2
    assert mock_client.submit_telemetry.call_count == 2
    assert len(test_queue_storage.get_pending()) == 0


def test_queue_sync_worker_exponential_backoff(test_queue_storage: QueueStorage):
    """Verify QueueSyncWorker triggers exponential backoff on network connection errors."""
    mock_client = MagicMock()
    mock_client.submit_telemetry.side_effect = AgentConnectionError("Server unreachable")

    test_queue_storage.enqueue({"cpu": 25.0, "idempotency_key": "sync-fail-1"})

    worker = QueueSyncWorker(test_queue_storage, mock_client, base_backoff_seconds=1.0)
    assert worker.can_attempt_sync() is True

    delivered = worker.sync_pending()
    assert delivered == 0
    # Should now be in backoff period
    assert worker.can_attempt_sync() is False
    assert worker._consecutive_failures == 1
    assert worker._current_backoff >= 0.8
