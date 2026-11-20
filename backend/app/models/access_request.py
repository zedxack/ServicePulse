"""
ServicePulse - Access Request Model
Centralized Access Governance entity for managing approval workflows:
- Organization Registration
- Organization Membership
- Role Privileges (Employee, Support, IT Admin, Company Admin, Executive)
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.organization_request import OrganizationRequest
    from backend.app.models.user import User


class AccessRequest(Base, TimestampMixin):
    """
    Centralized Access Request entity.
    Every privileged access, organization registration, and tenant role assignment
    requires authoritative review by the Primary Platform Owner.
    """
    __tablename__ = "access_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Request Type:
    # 'organization_registration', 'organization_membership',
    # 'employee_access', 'support_access', 'it_admin_access',
    # 'company_admin_access', 'executive_access'
    request_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Workflow Status: 'pending', 'approved', 'rejected', 'revoked'
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)

    applicant_email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    applicant_full_name: Mapped[str] = mapped_column(String(150), nullable=False)

    # Target Organization (Null for new organization registration)
    organization_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Submitting User (Null for anonymous public applicants)
    requester_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Target role requested
    target_role_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Link to OrganizationRequest if type is 'organization_registration'
    organization_request_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("organization_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    justification: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Client context
    client_ip: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Reviewer tracking (Designated Primary Platform Owner)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship("Organization")
    requester: Mapped[Optional["User"]] = relationship("User", foreign_keys=[requester_user_id])
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_id])
    organization_request: Mapped[Optional["OrganizationRequest"]] = relationship("OrganizationRequest")
