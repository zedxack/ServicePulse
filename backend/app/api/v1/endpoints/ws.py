"""
ServicePulse - Real-Time WebSocket & Ticket Issuance Endpoints
Author: Muhammadyusuf Usmonov
"""
import json
import logging
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel

from backend.app.core.dependencies import get_current_active_user
from backend.app.models.user import User
from backend.app.services.ws_manager import ticket_store, ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class WSTicketResponse(BaseModel):
    ticket: str
    expires_in: int = 30
    expires_in_seconds: int = 30


@router.post(
    "/ticket",
    response_model=WSTicketResponse,
    summary="Issue a short-lived single-use WebSocket authentication ticket",
)
async def issue_ws_ticket(
    current_user: User = Depends(get_current_active_user),
) -> WSTicketResponse:
    """
    Issue single-use ticket valid for 30 seconds.
    Prevents leaking long-lived JWT in browser WebSocket URL query parameters.
    """
    user_roles = [r.name for r in current_user.roles]
    ticket = await ticket_store.create_ticket(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        roles=user_roles,
        email=current_user.email,
        ttl_seconds=30,
    )
    return WSTicketResponse(ticket=ticket, expires_in=30, expires_in_seconds=30)


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    ticket: Optional[str] = Query(None, description="Short-lived single-use auth ticket"),
):
    """
    Real-time event stream WebSocket endpoint.
    Strictly validates and consumes single-use ticket.
    Binds connection to user and tenant without relying on client-supplied org ID.
    """
    if not ticket:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication ticket")
        return

    record = await ticket_store.consume_ticket(ticket)
    if not record:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired ticket")
        return

    conn = await ws_manager.connect(
        websocket=websocket,
        user_id=record.user_id,
        organization_id=record.organization_id,
        roles=record.roles,
        email=record.email,
    )

    try:
        # Send initial connection confirmation
        await websocket.send_text(
            json.dumps({
                "type": "connection:established",
                "organization_id": record.organization_id,
                "user_id": record.user_id,
                "message": "Connected to ServicePulse real-time monitoring event stream",
            })
        )

        while True:
            data_text = await websocket.receive_text()
            try:
                msg = json.loads(data_text)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except Exception:
                # Ignore malformed client messages
                pass

    except WebSocketDisconnect:
        await ws_manager.disconnect(conn)
    except Exception as exc:
        logger.warning("WebSocket exception for user %s: %s", record.user_id, exc)
        await ws_manager.disconnect(conn)
