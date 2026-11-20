"""
ServicePulse - User, Role & Auth Schemas
Pydantic v2
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


def _clean_email(v: Any) -> Any:
    if isinstance(v, str):
        return v.strip().lower()
    return v


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    primary_dashboard: str = "employee"
    organization_id: Optional[int] = None
    full_name: str
    roles: List[str] = []
    is_primary_owner: bool = False


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None
    all_sessions: bool = False


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None
    jti: Optional[str] = None


class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: Optional[str] = None


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    permissions: List[PermissionRead] = []


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    is_active: bool = True
    is_superuser: bool = False
    organization_id: Optional[int] = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: Any) -> Any:
        return _clean_email(v)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role_names: List[str] = ["employee"]
    role_name: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_roles(cls, data: Any) -> Any:
        if isinstance(data, dict):
            single_role = data.get("role_name")
            if single_role and not data.get("role_names"):
                data["role_names"] = [single_role]
            elif single_role and "role_names" in data and not data["role_names"]:
                data["role_names"] = [single_role]
        return data


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    role_names: Optional[List[str]] = None
    organization_id: Optional[int] = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: Any) -> Any:
        return _clean_email(v)


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: Any) -> Any:
        return _clean_email(v)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    roles: List[RoleRead] = []
    created_at: datetime
    last_login: Optional[datetime] = None
    primary_dashboard: str = "employee"
    is_primary_owner: bool = False
    organization_name: Optional[str] = None
