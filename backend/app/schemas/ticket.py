"""
ServicePulse - Helpdesk Tickets & Software Request Schemas
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TicketCommentCreate(BaseModel):
    comment: str = Field(..., min_length=1)


class TicketCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    author_id: int
    comment: str
    created_at: datetime


class TicketCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: str
    category: str = Field("general", max_length=50)
    priority: str = Field("medium", pattern="^(low|medium|high|urgent)$")
    device_id: Optional[int] = None
    organization_id: Optional[int] = None


class TicketUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    status: Optional[str] = Field(None, pattern="^(open|in_progress|waiting|resolved|closed)$")


class TicketAssign(BaseModel):
    assigned_to_id: int


class TicketResolve(BaseModel):
    resolution_notes: Optional[str] = None


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: Optional[int] = None
    title: str
    description: str
    category: str
    priority: str
    status: str
    author_id: int
    assigned_to_id: Optional[int] = None
    device_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    comments: List[TicketCommentRead] = []


class SoftwareRequestCreate(BaseModel):
    device_id: int
    software_name: str = Field(..., max_length=150)
    software_version: Optional[str] = Field(None, max_length=50)
    reason: str = Field(..., min_length=5)
    organization_id: Optional[int] = None


class SoftwareRequestReview(BaseModel):
    review_notes: Optional[str] = None


class SoftwareRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: Optional[int] = None
    user_id: int
    device_id: int
    software_name: str
    software_version: Optional[str]
    reason: str
    status: str
    reviewed_by_user_id: Optional[int]
    review_notes: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime
