"""
ServicePulse - Monitoring Models
Configuration, device state transitions, outage intervals, and maintenance windows.
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
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
    from backend.app.models.incident import Incident
    from backend.app.models.inventory import Device
    from backend.app.models.organization import Organization
    from backend.app.models.user import User


class DeviceMonitoringConfig(Base, TimestampMixin):
    """
    Per-device monitoring profile and administrative authorization.
    Controls probe frequency, ports, thresholds, and simulation mode.
    """
    __tablename__ = "device_monitoring_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_authorized: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ping_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Comma-separated TCP ports to probe e.g. "80,443,554,8291"
    tcp_ports: Mapped[Optional[str]] = mapped_column(String(255), default="80,443,554,8291", nullable=True)

    check_interval_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    timeout_seconds: Mapped[float] = mapped_column(Float, default=3.0, nullable=False)
    consecutive_failure_threshold: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # When True, requests to sample/unroutable addresses use deterministic simulation adapter
    simulation_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    device: Mapped["Device"] = relationship("Device", back_populates="monitoring_config")


class DeviceStateTransition(Base):
    """
    Audit record of device status transitions (online -> offline, offline -> online).
    """
    __tablename__ = "device_state_transitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    from_status: Mapped[str] = mapped_column(String(30), nullable=False)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    trigger_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    transition_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    device: Mapped["Device"] = relationship("Device", back_populates="state_transitions")


class OutageInterval(Base, TimestampMixin):
    """
    Verified downtime duration interval.
    Serves as the empirical foundation for duration-based SLA calculations.
    """
    __tablename__ = "outage_intervals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    incident_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    is_planned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    device: Mapped["Device"] = relationship("Device")
    incident: Mapped[Optional["Incident"]] = relationship("Incident")
    organization: Mapped[Optional["Organization"]] = relationship("Organization")


class MaintenanceWindow(Base, TimestampMixin):
    """
    Scheduled maintenance window.
    Downtime during active maintenance is excluded from SLA penalties.
    """
    __tablename__ = "maintenance_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    device_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    organization: Mapped["Organization"] = relationship("Organization")
    device: Mapped[Optional["Device"]] = relationship("Device")
    created_by: Mapped[Optional["User"]] = relationship("User")
