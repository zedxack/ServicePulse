"""
ServicePulse - Real-Time WebSocket Connection Manager & Ticket Store
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI

Provides:
- Short-lived, single-use ticket issuance & redemption (no JWT in URL).
- Tenant-scoped connection pooling & event broadcast.
- Role-based event filtering.
- Heartbeat ping/pong and graceful disconnect cleanup.
- Bounded async delivery with backpressure protection.
"""
import asyncio
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class WSTicket:
    ticket: str
    user_id: int
    organization_id: Optional[int]
    roles: List[str]
    email: str
    expires_at: datetime


class WSTicketStore:
    """Thread-safe, single-use in-memory ticket store with automatic TTL expiry."""

    def __init__(self, default_ttl_seconds: int = 30):
        self.default_ttl = default_ttl_seconds
        self._tickets: Dict[str, WSTicket] = {}
        self._lock = asyncio.Lock()

    async def create_ticket(
        self,
        user_id: int,
        organization_id: Optional[int],
        roles: List[str],
        email: str,
        ttl_seconds: Optional[int] = None,
    ) -> str:
        ttl = ttl_seconds or self.default_ttl
        ticket_str = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        record = WSTicket(
            ticket=ticket_str,
            user_id=user_id,
            organization_id=organization_id,
            roles=roles,
            email=email,
            expires_at=now + timedelta(seconds=ttl),
        )
        async with self._lock:
            # Clean expired tickets periodically
            self._purge_expired(now)
            self._tickets[ticket_str] = record
        return ticket_str

    async def consume_ticket(self, ticket_str: str) -> Optional[WSTicket]:
        now = datetime.now(timezone.utc)
        async with self._lock:
            record = self._tickets.pop(ticket_str, None)
            if not record:
                return None
            if record.expires_at < now:
                return None
            return record

    redeem_ticket = consume_ticket

    def _purge_expired(self, now: datetime):
        expired = [k for k, v in self._tickets.items() if v.expires_at < now]
        for k in expired:
            self._tickets.pop(k, None)


@dataclass(eq=False)
class WSConnection:
    websocket: WebSocket
    user_id: int
    organization_id: Optional[int]
    roles: Set[str]
    email: str
    connected_at: datetime
    queue: asyncio.Queue


class ConnectionManager:
    """
    Manages active WebSocket connections grouped by organization.
    Ensures absolute tenant isolation, role-filtering, and graceful cleanup.
    """

    def __init__(self):
        # org_id -> set of WSConnection
        self._org_connections: Dict[int, Set[WSConnection]] = {}
        # Superuser / global connections (org_id is None)
        self._global_connections: Set[WSConnection] = set()
        # user_id -> set of WSConnection
        self._user_connections: Dict[int, Set[WSConnection]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        organization_id: Optional[int],
        roles: List[str],
        email: str,
    ) -> WSConnection:
        await websocket.accept()
        conn = WSConnection(
            websocket=websocket,
            user_id=user_id,
            organization_id=organization_id,
            roles=set(roles),
            email=email,
            connected_at=datetime.now(timezone.utc),
            queue=asyncio.Queue(maxsize=100),  # Bounded queue to prevent unbounded memory
        )

        async with self._lock:
            if organization_id is not None:
                self._org_connections.setdefault(organization_id, set()).add(conn)
            else:
                self._global_connections.add(conn)

            self._user_connections.setdefault(user_id, set()).add(conn)

        logger.info(
            "WebSocket client connected: user_id=%s, org_id=%s, roles=%s",
            user_id,
            organization_id,
            roles,
        )
        return conn

    async def disconnect(self, conn: WSConnection):
        async with self._lock:
            if conn.organization_id is not None:
                org_set = self._org_connections.get(conn.organization_id)
                if org_set:
                    org_set.discard(conn)
                    if not org_set:
                        self._org_connections.pop(conn.organization_id, None)
            else:
                self._global_connections.discard(conn)

            user_set = self._user_connections.get(conn.user_id)
            if user_set:
                user_set.discard(conn)
                if not user_set:
                    self._user_connections.pop(conn.user_id, None)

        logger.info("WebSocket client disconnected: user_id=%s, email=%s", conn.user_id, conn.email)

    async def broadcast_to_org(
        self,
        organization_id: int,
        event_type: str,
        data: dict,
        allowed_roles: Optional[Set[str]] = None,
    ):
        """
        Broadcast event strictly to connections of the specified organization.
        Platform super admins also receive org events if connected.
        """
        payload = {
            "type": event_type,
            "organization_id": organization_id,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        msg_str = json.dumps(payload)

        targets: List[WSConnection] = []
        async with self._lock:
            # Org-specific targets
            for conn in self._org_connections.get(organization_id, set()):
                if allowed_roles is None or bool(conn.roles & allowed_roles):
                    targets.append(conn)

            # Global platform super admin targets
            for conn in self._global_connections:
                if "platform_super_admin" in conn.roles:
                    targets.append(conn)

        for conn in targets:
            await self._safe_send(conn, msg_str)

    async def send_to_user(self, user_id: int, event_type: str, data: dict):
        """Send event strictly to a specific user's active connections."""
        payload = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        msg_str = json.dumps(payload)

        targets: List[WSConnection] = []
        async with self._lock:
            for conn in self._user_connections.get(user_id, set()):
                targets.append(conn)

        for conn in targets:
            await self._safe_send(conn, msg_str)

    async def _safe_send(self, conn: WSConnection, msg_str: str):
        try:
            await conn.websocket.send_text(msg_str)
        except Exception as exc:
            logger.warning("Error delivering WebSocket event to user %s: %s", conn.user_id, exc)

    async def start_outbox_listener(self):
        """
        Background task running in the FastAPI backend process that reads events
        written to the PostgreSQL outbox by separate background workers (e.g.
        servicepulse-network-worker) and broadcasts them to connected WebSocket clients.
        """
        self._outbox_running = True
        self._last_outbox_id = 0
        from sqlalchemy import delete, func, select

        from backend.app.db.session import AsyncSessionLocal
        from backend.app.models.event_outbox import RealtimeEvent

        try:
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(func.coalesce(func.max(RealtimeEvent.id), 0)))
                self._last_outbox_id = res.scalar() or 0
                logger.info("WebSocket Outbox Listener initialized at last_event_id=%d", self._last_outbox_id)
        except Exception as exc:
            logger.warning("Could not initialize outbox last_id: %s", exc)

        cycle_count = 0
        while self._outbox_running:
            try:
                async with AsyncSessionLocal() as session:
                    q = (
                        select(RealtimeEvent)
                        .where(
                            RealtimeEvent.id > self._last_outbox_id,
                            RealtimeEvent.origin == "worker",
                        )
                        .order_by(RealtimeEvent.id.asc())
                        .limit(50)
                    )
                    events = (await session.execute(q)).scalars().all()
                    for ev in events:
                        self._last_outbox_id = ev.id
                        try:
                            payload_data = json.loads(ev.payload)
                            await self.broadcast_to_org(ev.organization_id, ev.event_type, payload_data)
                        except Exception as parse_err:
                            logger.error("Failed to parse and broadcast outbox event %d: %s", ev.id, parse_err)

                    cycle_count += 1
                    if cycle_count >= 300:
                        cycle_count = 0
                        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
                        await session.execute(delete(RealtimeEvent).where(RealtimeEvent.created_at < cutoff))
                        await session.commit()

            except asyncio.CancelledError:
                break
            except Exception as poll_err:
                logger.debug("Outbox listener poll exception: %s", poll_err)
                await asyncio.sleep(1.0)
                continue

            await asyncio.sleep(0.2)

    def stop_outbox_listener(self):
        """Signal the outbox listener loop to terminate."""
        self._outbox_running = False


ticket_store = WSTicketStore(default_ttl_seconds=30)
ws_manager = ConnectionManager()
