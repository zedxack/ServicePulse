"""
ServicePulse - Platform Settings & Owner Governance Model
Singleton entity storing global platform settings and immutable Primary Platform Owner reference.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.user import User


class PlatformSettings(Base, TimestampMixin):
    """
    Singleton system configuration table (id=1).
    Establishes the designated Primary Platform Owner reference and global platform policies.
    """
    __tablename__ = "platform_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    primary_owner_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True
    )
    platform_name: Mapped[str] = mapped_column(String(100), default="ServicePulse", nullable=False)
    allow_public_registration: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    bootstrap_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    primary_owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[primary_owner_id])
