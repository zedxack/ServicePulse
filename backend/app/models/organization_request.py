"""
ServicePulse - Organization Onboarding Request Model
Pending approval workflow for new tenant organizations.
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.user import User


class OrganizationRequest(Base, TimestampMixin):
    __tablename__ = "organization_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    org_name: Mapped[str] = mapped_column(String(150), nullable=False)
    org_slug: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    org_email: Mapped[str] = mapped_column(String(255), nullable=False)
    org_domain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    contact_full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    # Store initial admin password securely hashed with Argon2id
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Workflow Status: 'pending', 'approved', 'rejected'
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)

    reviewed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Populated upon approval
    created_organization_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True
    )
    created_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_id], lazy="selectin")
    created_organization: Mapped[Optional["Organization"]] = relationship("Organization", foreign_keys=[created_organization_id], lazy="selectin")
    created_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_user_id], lazy="selectin")
