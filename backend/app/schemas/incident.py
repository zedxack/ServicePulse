"""
ServicePulse - Incident Schemas
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class IncidentEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    event_type: str
    message: str
    payload: Optional[str] = None
    created_by_user_id: Optional[int] = None
    created_at: datetime


class IncidentCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: str
    severity: str = Field("warning", pattern="^(critical|warning|info)$")
    device_id: Optional[int] = None
    organization_id: Optional[int] = None
    fingerprint: Optional[str] = Field(None, max_length=128)


class IncidentAssign(BaseModel):
    assigned_to_user_id: int


class IncidentAcknowledge(BaseModel):
    notes: Optional[str] = None


class IncidentResolve(BaseModel):
    resolution_notes: str = Field(..., min_length=3)


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: Optional[int] = None
    device_id: Optional[int]
    fingerprint: str
    active_dedup_key: Optional[str] = None
    title: str
    description: str
    severity: str
    status: str
    occurrence_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    resolved_at: Optional[datetime] = None
    assigned_to_user_id: Optional[int] = None
    resolution_notes: Optional[str] = None
    events: List[IncidentEventRead] = []
    created_at: datetime


class IncidentListResponse(BaseModel):
    total: int
    items: List[IncidentRead]
