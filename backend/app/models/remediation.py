"""
ServicePulse - Automated Remediation Models
Configurable rules, execution records, verification & audit history
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
    from backend.app.models.agent import AgentCommand
    from backend.app.models.incident import Incident
    from backend.app.models.inventory import Device
    from backend.app.models.organization import Organization
    from backend.app.models.user import User


class RemediationRule(Base, TimestampMixin):
    __tablename__ = "remediation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    trigger_condition: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Allowlisted action: restart_windows_service, restart_agent, run_diagnostics, check_gateway, notify_admin
    action_name: Mapped[str] = mapped_column(String(100), nullable=False)
    action_parameters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)

    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="remediation_rules")
    executions: Mapped[List["RemediationExecution"]] = relationship(
        "RemediationExecution",
        back_populates="rule"
    )


class RemediationExecution(Base, TimestampMixin):
    __tablename__ = "remediation_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rule_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("remediation_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    incident_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    device_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    agent_command_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("agent_commands.id", ondelete="SET NULL", use_alter=True, name="fk_remediation_executions_agent_command_id"),
        nullable=True,
        index=True
    )
    is_simulation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status: pending_approval, approved, rejected, executing, success, failure
    status: Mapped[str] = mapped_column(String(30), default="pending_approval", nullable=False, index=True)

    # Verification: pending, verified_success, verification_failed
    verification_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)

    approved_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    execution_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    rule: Mapped[RemediationRule] = relationship("RemediationRule", back_populates="executions")
    incident: Mapped["Incident"] = relationship("Incident", back_populates="remediation_executions")
    device: Mapped[Optional["Device"]] = relationship("Device")
    agent_command: Mapped[Optional["AgentCommand"]] = relationship("AgentCommand", foreign_keys=[agent_command_id])
    approved_by: Mapped[Optional["User"]] = relationship("User")
