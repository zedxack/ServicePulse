"""
ServicePulse - Real-Time Event Outbox Model
Cross-process event outbox ensuring delivery between network worker and WebSocket backend.
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class RealtimeEvent(Base):
    """
    Persistent event outbox table.
    Enables asynchronous, reliable cross-process event broadcasting across
    isolated containers (e.g. servicepulse-network-worker to servicepulse-backend).
    """
    __tablename__ = "realtime_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    target_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    origin: Mapped[str] = mapped_column(String(50), default="worker", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
