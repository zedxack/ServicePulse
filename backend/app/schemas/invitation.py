"""
ServicePulse - Invitation Schemas
Pydantic v2
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class InvitationCreate(BaseModel):
    role_id: int = Field(..., description="Target role ID for invited user")
    organization_id: Optional[int] = Field(None, description="Target organization ID (Super Admin only; defaults to user's org)")
    invited_email: Optional[EmailStr] = Field(None, description="Optional restricted email for this invitation")
    max_uses: int = Field(default=1, ge=1, le=1000, description="Maximum number of times this invitation can be used")
    expires_in_days: int = Field(default=7, ge=1, le=90, description="Expiration time in days")


class InvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    role_id: int
    role_name: Optional[str] = None
    token_prefix: str
    max_uses: int
    uses_count: int
    expires_at: datetime
    is_revoked: bool
    is_valid: bool
    invited_email: Optional[str] = None
    created_at: datetime


class InvitationCreateResponse(BaseModel):
    invitation: InvitationRead
    raw_token: str = Field(..., description="Full secret token string to share with the invitee. Shown only once.")


class InvitationValidateRequest(BaseModel):
    invitation_code: str = Field(..., min_length=8, description="Invitation code or full token string")


class InvitationValidateResponse(BaseModel):
    valid: bool
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    invited_email: Optional[str] = None
    error_message: Optional[str] = None


class JoinOrganizationRequest(BaseModel):
    invitation_code: str = Field(..., min_length=8, description="Valid invitation code")
    full_name: str = Field(..., min_length=2, max_length=150, description="User's full name")
    email: EmailStr = Field(..., description="User's corporate email address")
    password: str = Field(..., min_length=8, description="Secure password meeting complexity criteria")
