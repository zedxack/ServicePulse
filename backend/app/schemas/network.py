"""
ServicePulse - Network Check Schemas
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NetworkCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    check_type: str
    port: Optional[int] = None
    is_successful: bool
    response_time_ms: float
    packet_loss_percent: float
    error_message: Optional[str] = None
    checked_at: datetime
