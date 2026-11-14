"""
ServicePulse - Distributed Worker Leadership & Advisory Lock Manager
Provides PostgreSQL-backed distributed singleton worker leases using session advisory locks.
Guarantees only one active worker instance owns the monitoring loop, safely refusing leadership
to secondary instances, and automatically recovering upon worker shutdown or process crash.
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
import asyncio
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.session import engine

# 32-bit positive integer identifying ServicePulse Network Monitoring Worker singleton lease
NETWORK_WORKER_ADVISORY_LOCK_ID = 84729103


class WorkerLeaseManager:
    """
    Manages database-backed singleton worker leadership.
    Uses PostgreSQL session-level advisory locks (pg_try_advisory_lock).
    PostgreSQL guarantees immediate release upon connection close or process crash.
    Provides in-memory fallback for SQLite test environments.
    """
    _sqlite_locks = set()
    _sqlite_lock_sync = asyncio.Lock()

    def __init__(
        self,
        lock_id: int = NETWORK_WORKER_ADVISORY_LOCK_ID,
        custom_engine: Optional[AsyncEngine] = None
    ):
        self.lock_id = lock_id
        self._custom_engine = custom_engine
        self._connection: Optional[AsyncConnection] = None
        self._dedicated_engine: Optional[AsyncEngine] = None
        self._has_lock = False

    async def acquire_lease(self) -> bool:
        """
        Attempt to acquire singleton worker lease.
        Returns True if acquired (this instance is leader), False otherwise.
        """
        if self._has_lock:
            return True

        target_engine = self._custom_engine or engine
        dialect = target_engine.dialect.name
        if dialect == "postgresql":
            conn = None
            try:
                # Create dedicated NullPool engine to bind connection to the active event loop
                self._dedicated_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
                conn = await self._dedicated_engine.connect()
                res = await conn.execute(
                    text("SELECT pg_try_advisory_lock(:lock_id)"),
                    {"lock_id": self.lock_id}
                )
                acquired = bool(res.scalar())
                if acquired:
                    self._connection = conn
                    self._has_lock = True
                    logger.info("Successfully acquired PostgreSQL worker lease (lock_id=%d).", self.lock_id)
                    return True
                else:
                    await conn.close()
                    await self._dedicated_engine.dispose()
                    self._dedicated_engine = None
                    logger.warning(
                        "Another worker instance holds the PostgreSQL advisory lock (lock_id=%d). Refusing leadership.",
                        self.lock_id
                    )
                    return False
            except Exception as e:
                logger.error("Error acquiring PostgreSQL advisory lock: %s", str(e))
                if conn:
                    await conn.close()
                if self._dedicated_engine:
                    await self._dedicated_engine.dispose()
                    self._dedicated_engine = None
                return False
        else:
            # SQLite / in-memory test environment fallback
            async with self._sqlite_lock_sync:
                if self.lock_id in self._sqlite_locks:
                    logger.warning("Worker lease (lock_id=%d) is already held. Refusing leadership.", self.lock_id)
                    return False
                self._sqlite_locks.add(self.lock_id)
                self._has_lock = True
                logger.info("Acquired SQLite worker lease (lock_id=%d).", self.lock_id)
                return True

    async def release_lease(self) -> None:
        """Explicitly release the held worker lease."""
        if not self._has_lock:
            return

        target_engine = self._custom_engine or engine
        dialect = target_engine.dialect.name
        if dialect == "postgresql" and self._connection:
            try:
                await self._connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": self.lock_id}
                )
            except Exception as e:
                logger.warning("Error unlocking advisory lock: %s", str(e))
            finally:
                await self._connection.close()
                self._connection = None
                if self._dedicated_engine:
                    await self._dedicated_engine.dispose()
                    self._dedicated_engine = None
                self._has_lock = False
                logger.info("Released PostgreSQL worker lease (lock_id=%d).", self.lock_id)
        else:
            async with self._sqlite_lock_sync:
                self._sqlite_locks.discard(self.lock_id)
                self._has_lock = False
                logger.info("Released SQLite worker lease (lock_id=%d).", self.lock_id)

    @property
    def is_leader(self) -> bool:
        return self._has_lock
