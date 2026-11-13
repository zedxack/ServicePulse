"""
ServicePulse - Incident & IncidentEvent Models
Concurrency-safe deduplication, lifecycle tracking & audit history
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.inventory import Device
    from backend.app.models.organization import Organization
    from backend.app.models.remediation import RemediationExecution
    from backend.app.models.user import User


class Incident(Base, TimestampMixin):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    device_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Deduplication fingerprint (e.g. hash of device_id + failure_type + target_port)
    fingerprint: Mapped[str] = mapped_column(String(128), index=True, nullable=False)

    # Active deduplication key (unique while incident is active; set to NULL upon resolution)
    active_dedup_key: Mapped[Optional[str]] = mapped_column(
        String(128),
        unique=True,
        nullable=True,
        index=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Severity: critical, warning, info
    severity: Mapped[str] = mapped_column(String(20), default="warning", nullable=False, index=True)

    # Status: open, acknowledged, in_progress, resolved, closed
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False, index=True)

    # Deduplication and occurrence tracking
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    assigned_to_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    device: Mapped[Optional["Device"]] = relationship("Device", back_populates="incidents")
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="incidents")
    assigned_to: Mapped[Optional["User"]] = relationship("User")
    events: Mapped[List["IncidentEvent"]] = relationship(
        "IncidentEvent",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="desc(IncidentEvent.created_at)"
    )
    remediation_executions: Mapped[List["RemediationExecution"]] = relationship(
        "RemediationExecution",
        back_populates="incident"
    )


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Event types: detected, deduplicated, status_change, assigned, comment, remediation_dispatched, resolved
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    incident: Mapped[Incident] = relationship("Incident", back_populates="events")
    created_by: Mapped[Optional["User"]] = relationship("User")
