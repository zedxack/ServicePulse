"""
ServicePulse - Notification Schemas
Author: Muhammadyusuf Usmonov
"""
import json
from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NotificationBase(BaseModel):
    title: str = Field(..., max_length=200)
    message: str
    severity: str = Field("info", pattern=r"^(info|warning|error|critical)$")
    category: str = Field("device", pattern=r"^(device|incident|remediation|telemetry|software|security|ticket|system)$")
    data: Optional[Union[str, dict]] = None

    @field_validator("data", mode="before")
    @classmethod
    def serialize_data(cls, v):
        if isinstance(v, dict):
            return json.dumps(v)
        return v


class NotificationCreate(NotificationBase):
    organization_id: int
    user_id: Optional[int] = None
    target_role: Optional[str] = None
    fingerprint: str = Field(..., max_length=128)


class NotificationRead(NotificationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    user_id: Optional[int] = None
    target_role: Optional[str] = None
    fingerprint: str
    is_read: bool
    is_dismissed: bool
    read_at: Optional[datetime] = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    total: int
    unread_count: int
    items: List[NotificationRead]


class UnreadCountResponse(BaseModel):
    unread_count: int
