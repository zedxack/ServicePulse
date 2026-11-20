"""
ServicePulse - Access Request Schemas
Pydantic v2
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _clean_email(v: Any) -> Any:
    if isinstance(v, str):
        return v.strip().lower()
    return v


class AccessRequestCreate(BaseModel):
    request_type: str = Field(
        ...,
        description="Type of access requested: 'organization_membership', 'employee_access', 'support_access', 'it_admin_access', 'company_admin_access', 'executive_access'"
    )
    applicant_email: EmailStr = Field(..., description="Corporate email address of applicant")
    applicant_full_name: str = Field(..., min_length=2, max_length=150, description="Full name of applicant")
    organization_id: Optional[int] = Field(None, description="Target organization ID")
    target_role_name: Optional[str] = Field(None, description="Requested RBAC role name")
    justification: Optional[str] = Field(None, max_length=500, description="Business justification for requested access")

    @field_validator("applicant_email", mode="before")
    @classmethod
    def normalize_email(cls, v: Any) -> Any:
        return _clean_email(v)


class AccessRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_type: str
    status: str
    applicant_email: str
    applicant_full_name: str
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    requester_user_id: Optional[int] = None
    target_role_name: Optional[str] = None
    organization_request_id: Optional[int] = None
    justification: Optional[str] = None
    rejection_reason: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    reviewed_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class AccessRequestReject(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500, description="Mandatory reason for rejection")


class AccessRequestStats(BaseModel):
    pending_count: int
    approved_count: int
    rejected_count: int
    total_count: int
