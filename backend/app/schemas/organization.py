"""
ServicePulse - Organization / Tenant Schemas
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class OrganizationBase(BaseModel):
    name: str = Field(..., max_length=150)
    slug: str = Field(..., max_length=50)
    domain: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    max_devices: int = Field(100, ge=1)


class OrganizationCreate(BaseModel):
    name: str = Field(..., max_length=150)
    slug: str = Field(..., max_length=50)
    domain: Optional[str] = Field(None, max_length=100)
    max_devices: int = Field(100, ge=1)


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    domain: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    max_devices: Optional[int] = Field(None, ge=1)


class OrganizationRead(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
