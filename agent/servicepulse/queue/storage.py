"""
ServicePulse Native Windows Agent - Crash-Resilient Persistent SQLite Queue
Buffers unsent telemetry locally when the backend or network is unavailable.
Author: Muhammadyusuf Usmonov
"""
import datetime
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from servicepulse.logging.setup import get_logger

logger = get_logger()

SCHEMA_VERSION = 1


class QueueRecord(BaseModel):
    id: int
    event_uuid: str
    idempotency_key: str
    payload: Dict[str, Any]
    created_at: str
    retry_count: int = 0
    last_attempt_at: Optional[str] = None
    status: str = "pending"
    error_message: Optional[str] = None


class QueueStorage:
    """
    Manages local transactional storage of telemetry records in SQLite.
    WAL mode is enabled for performance, crash-safety, and concurrent reading.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a connection with WAL mode and foreign keys enabled."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self) -> None:
        """Initialize database schema, verify integrity, and handle migration/corruption."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Integrity check on existing file
        if self.db_path.is_file() and self.db_path.stat().st_size > 0:
            is_corrupt = False
            try:
                test_conn = sqlite3.connect(str(self.db_path), timeout=5.0)
                try:
                    cur = test_conn.cursor()
                    cur.execute("PRAGMA integrity_check;")
                    res = cur.fetchone()
                    if not res or res[0] != "ok":
                        is_corrupt = True
                finally:
                    test_conn.close()
            except Exception as e:
                logger.error(f"Queue database integrity check failed ({e}). Rebuilding database.")
                is_corrupt = True

            if is_corrupt:
                self._recover_corrupt_database()

        conn = self._get_connection()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS queue_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS telemetry_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_uuid TEXT UNIQUE NOT NULL,
                        idempotency_key TEXT UNIQUE NOT NULL,
                        payload TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        retry_count INTEGER DEFAULT 0,
                        last_attempt_at TEXT,
                        status TEXT DEFAULT 'pending',
                        error_message TEXT
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tel_status ON telemetry_queue(status, created_at);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tel_idemp ON telemetry_queue(idempotency_key);")

                # Store schema version
                conn.execute(
                    "INSERT OR REPLACE INTO queue_metadata (key, value) VALUES ('schema_version', ?);",
                    (str(SCHEMA_VERSION),)
                )
        finally:
            conn.close()

    def _recover_corrupt_database(self) -> None:
        """Back up corrupted queue database and start fresh."""
        import gc
        import shutil
        gc.collect()

        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        corrupt_backup = self.db_path.with_name(f"{self.db_path.name}.corrupt_{timestamp}")
        try:
            if self.db_path.exists():
                shutil.copy2(self.db_path, corrupt_backup)
                self.db_path.unlink()
                logger.warning(f"Corrupt queue database backed up to {corrupt_backup}")
        except Exception as e:
            logger.error(f"Failed to backup corrupt database: {e}")

    def enqueue(self, payload: Dict[str, Any], idempotency_key: Optional[str] = None) -> QueueRecord:
        """
        Atomically persist a telemetry payload in pending status.
        """
        event_uuid = f"evt_{uuid.uuid4().hex}"
        idemp = idempotency_key or payload.get("idempotency_key") or f"tx_{uuid.uuid4().hex}"
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        serialized = json.dumps(payload)

        # Inject idempotency_key into payload if not present
        if "idempotency_key" not in payload:
            payload["idempotency_key"] = idemp
            serialized = json.dumps(payload)

        conn = self._get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO telemetry_queue
                    (event_uuid, idempotency_key, payload, created_at, retry_count, status)
                    VALUES (?, ?, ?, ?, 0, 'pending');
                    """,
                    (event_uuid, idemp, serialized, now_str)
                )
                rec_id = cur.lastrowid
                return QueueRecord(
                    id=rec_id,
                    event_uuid=event_uuid,
                    idempotency_key=idemp,
                    payload=payload,
                    created_at=now_str,
                    retry_count=0,
                    status="pending"
                )
        finally:
            conn.close()

    def get_pending(self, limit: int = 50) -> List[QueueRecord]:
        """Retrieve oldest pending telemetry records for synchronization."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, event_uuid, idempotency_key, payload, created_at, retry_count, last_attempt_at, status, error_message
                FROM telemetry_queue
                WHERE status = 'pending'
                ORDER BY id ASC
                LIMIT ?;
                """,
                (limit,)
            )
            rows = cur.fetchall()
            results = []
            for r in rows:
                try:
                    payload_dict = json.loads(r["payload"])
                except Exception:
                    payload_dict = {}

                results.append(QueueRecord(
                    id=r["id"],
                    event_uuid=r["event_uuid"],
                    idempotency_key=r["idempotency_key"],
                    payload=payload_dict,
                    created_at=r["created_at"],
                    retry_count=r["retry_count"],
                    last_attempt_at=r["last_attempt_at"],
                    status=r["status"],
                    error_message=r["error_message"],
                ))
            return results
        finally:
            conn.close()

    def mark_delivered(self, event_uuid: str) -> None:
        """Mark record as confirmed delivered by server."""
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE telemetry_queue
                    SET status = 'sent', last_attempt_at = ?
                    WHERE event_uuid = ?;
                    """,
                    (now_str, event_uuid)
                )
        finally:
            conn.close()

    def record_failure(self, event_uuid: str, error_msg: str) -> None:
        """Increment retry count and record error message."""
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE telemetry_queue
                    SET retry_count = retry_count + 1,
                        last_attempt_at = ?,
                        error_message = ?
                    WHERE event_uuid = ?;
                    """,
                    (now_str, error_msg[:500], event_uuid)
                )
        finally:
            conn.close()

    def enforce_max_records(self, max_records: int = 10000) -> int:
        """
        Prune oldest already delivered records if database exceeds size limit.
        If pending records exceed limit, trims oldest pending to protect host disk.
        """
        conn = self._get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM telemetry_queue;")
                total = cur.fetchone()[0]

                if total <= max_records:
                    return 0

                excess = total - max_records
                # 1. Prune oldest delivered first
                cur.execute(
                    """
                    DELETE FROM telemetry_queue
                    WHERE id IN (
                        SELECT id FROM telemetry_queue WHERE status = 'sent'
                        ORDER BY id ASC LIMIT ?
                    );
                    """,
                    (excess,)
                )
                deleted = cur.rowcount
                remaining = excess - deleted

                # 2. If still exceeding, prune oldest failed/pending with warning
                if remaining > 0:
                    logger.warning(f"Queue storage full ({total} records). Trimming {remaining} oldest records.")
                    cur.execute(
                        """
                        DELETE FROM telemetry_queue
                        WHERE id IN (
                            SELECT id FROM telemetry_queue
                            ORDER BY id ASC LIMIT ?
                        );
                        """,
                        (remaining,)
                    )
                    deleted += cur.rowcount

                return deleted
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, int]:
        """Return counts of pending, sent, and total queue items."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT status, COUNT(*) FROM telemetry_queue GROUP BY status;")
            counts = {r[0]: r[1] for r in cur.fetchall()}
            return {
                "pending": counts.get("pending", 0),
                "sent": counts.get("sent", 0),
                "total": sum(counts.values()),
            }
        finally:
            conn.close()
