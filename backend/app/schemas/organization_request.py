"""
ServicePulse - Organization Onboarding Request Schemas
Pydantic v2
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationRequestCreate(BaseModel):
    org_name: str = Field(..., min_length=2, max_length=150, description="Organization or Enterprise Name")
    org_slug: Optional[str] = Field(None, min_length=2, max_length=50, description="Unique slug identifier (generated if omitted)")
    org_email: EmailStr = Field(..., description="Corporate primary contact/billing email")
    org_domain: Optional[str] = Field(None, max_length=100, description="Organization corporate email domain (e.g. acme.uz)")
    contact_full_name: str = Field(..., min_length=2, max_length=150, description="Initial Company Administrator Full Name")
    contact_email: EmailStr = Field(..., description="Administrator corporate email address")
    password: str = Field(..., min_length=8, description="Secure administrator password")
    phone: Optional[str] = Field(None, max_length=50, description="Contact phone number")
    website: Optional[str] = Field(None, max_length=255, description="Official company website URL")


class OrganizationRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    org_name: str
    org_slug: str
    org_email: str
    org_domain: Optional[str] = None
    contact_full_name: str
    contact_email: str
    phone: Optional[str] = None
    website: Optional[str] = None
    status: str
    rejection_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by_id: Optional[int] = None
    created_organization_id: Optional[int] = None
    created_user_id: Optional[int] = None
    created_at: datetime


class OrganizationRequestReject(BaseModel):
    reason: Optional[str] = Field(None, max_length=500, description="Reason for rejection provided to applicant")
