"""
ServicePulse - Multi-Tenant Organization / Tenant Model
Author: Muhammadyusuf Usmonov
"""
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.agent import Agent
    from backend.app.models.audit import AuditLog
    from backend.app.models.incident import Incident
    from backend.app.models.inventory import Building, Device
    from backend.app.models.remediation import RemediationRule
    from backend.app.models.ticket import SoftwareRequest, Ticket
    from backend.app.models.user import User


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    max_devices: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="organization"
    )
    buildings: Mapped[List["Building"]] = relationship(
        "Building",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    devices: Mapped[List["Device"]] = relationship(
        "Device",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    agents: Mapped[List["Agent"]] = relationship(
        "Agent",
        back_populates="organization"
    )
    incidents: Mapped[List["Incident"]] = relationship(
        "Incident",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    software_requests: Mapped[List["SoftwareRequest"]] = relationship(
        "SoftwareRequest",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    remediation_rules: Mapped[List["RemediationRule"]] = relationship(
        "RemediationRule",
        back_populates="organization"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="organization"
    )
