"""
ServicePulse - Agent, Telemetry & AgentCommand Models
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.inventory import Device


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
        index=True
    )
    agent_uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    api_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Status: pending, active, offline, suspended
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(30), default="1.0.0", nullable=False)
    hostname: Mapped[str] = mapped_column(String(150), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    os_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    device: Mapped[Optional["Device"]] = relationship("Device", back_populates="agent")
    telemetry_records: Mapped[List["AgentTelemetry"]] = relationship(
        "AgentTelemetry",
        back_populates="agent",
        cascade="all, delete-orphan",
        order_by="desc(AgentTelemetry.recorded_at)"
    )
    commands: Mapped[List["AgentCommand"]] = relationship(
        "AgentCommand",
        back_populates="agent",
        cascade="all, delete-orphan"
    )


class AgentTelemetry(Base, TimestampMixin):
    __tablename__ = "agent_telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    cpu_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ram_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ram_used_mb: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ram_total_mb: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    disk_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    disk_used_gb: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    disk_total_gb: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Windows-specific system status
    windows_activation_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    windows_defender_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    agent: Mapped[Agent] = relationship("Agent", back_populates="telemetry_records")


class AgentCommand(Base, TimestampMixin):
    __tablename__ = "agent_commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    device_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Allowlisted action e.g. restart_service, restart_agent, check_network, ping_gateway
    action_name: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status: pending, dispatched, executed, failed, timeout, rejected
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)

    # Verification: pending, verified_success, verification_failed, unverified
    verification_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)

    execution_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    requested_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    agent: Mapped[Agent] = relationship("Agent", back_populates="commands")
    device: Mapped[Optional["Device"]] = relationship("Device", back_populates="commands")
