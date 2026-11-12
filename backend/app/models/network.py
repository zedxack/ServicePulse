"""
ServicePulse - Network Monitoring Models
ICMP ping & TCP port checks history
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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.inventory import Device


class NetworkCheck(Base, TimestampMixin):
    __tablename__ = "network_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Types: icmp_ping, tcp_port
    check_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    is_successful: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    response_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    packet_loss_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    device: Mapped["Device"] = relationship("Device", back_populates="network_checks")
