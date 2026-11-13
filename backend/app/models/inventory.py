"""
ServicePulse - Inventory Infrastructure Models
Building -> Floor -> Room -> Device
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.agent import Agent, AgentCommand
    from backend.app.models.incident import Incident
    from backend.app.models.monitoring import (
        DeviceMonitoringConfig,
        DeviceStateTransition,
    )
    from backend.app.models.network import NetworkCheck
    from backend.app.models.organization import Organization


class Building(Base, TimestampMixin):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_sample_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="buildings")
    floors: Mapped[List["Floor"]] = relationship(
        "Floor",
        back_populates="building",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class Floor(Base, TimestampMixin):
    __tablename__ = "floors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    building_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_sample_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    building: Mapped[Building] = relationship("Building", back_populates="floors")
    rooms: Mapped[List["Room"]] = relationship(
        "Room",
        back_populates="floor",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class Room(Base, TimestampMixin):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    floor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("floors.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    room_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_sample_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    floor: Mapped[Floor] = relationship("Floor", back_populates="rooms")
    devices: Mapped[List["Device"]] = relationship(
        "Device",
        back_populates="room",
        lazy="selectin"
    )


class Device(Base, TimestampMixin):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    room_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("rooms.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    hostname: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    mac_address: Mapped[Optional[str]] = mapped_column(String(17), nullable=True)

    # Types: server, workstation, router, switch, access_point, ip_camera, other
    device_type: Mapped[str] = mapped_column(String(50), default="workstation", nullable=False, index=True)
    operating_system: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status: online, offline, warning, unknown
    status: Mapped[str] = mapped_column(String(30), default="unknown", nullable=False, index=True)
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_sample_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    room: Mapped[Optional[Room]] = relationship("Room", back_populates="devices")
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="devices")
    agent: Mapped[Optional["Agent"]] = relationship("Agent", back_populates="device", uselist=False)
    network_checks: Mapped[List["NetworkCheck"]] = relationship(
        "NetworkCheck",
        back_populates="device",
        cascade="all, delete-orphan"
    )
    incidents: Mapped[List["Incident"]] = relationship(
        "Incident",
        back_populates="device"
    )
    commands: Mapped[List["AgentCommand"]] = relationship(
        "AgentCommand",
        back_populates="device"
    )
    monitoring_config: Mapped[Optional["DeviceMonitoringConfig"]] = relationship(
        "DeviceMonitoringConfig",
        back_populates="device",
        uselist=False,
        cascade="all, delete-orphan"
    )
    state_transitions: Mapped[List["DeviceStateTransition"]] = relationship(
        "DeviceStateTransition",
        back_populates="device",
        cascade="all, delete-orphan",
        order_by="desc(DeviceStateTransition.transition_at)"
    )
