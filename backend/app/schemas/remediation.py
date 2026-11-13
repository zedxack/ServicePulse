"""
ServicePulse - Automated Remediation Schemas
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RemediationRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_condition: str
    target_device_type: Optional[str] = "workstation"
    action_name: str = "restart_service"
    action_parameters: Optional[str] = None
    is_active: bool = True
    requires_approval: bool = False


class RemediationRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    trigger_condition: str
    target_device_type: Optional[str] = None
    action_name: str
    action_parameters: Optional[str] = None
    is_active: bool
    requires_approval: bool
    created_at: datetime


class RemediationExecutionCreate(BaseModel):
    rule_id: int
    incident_id: int
    device_id: Optional[int] = None


class RemediationExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_id: int
    incident_id: int
    device_id: Optional[int] = None
    status: str
    verification_status: str
    approved_by_user_id: Optional[int] = None
    execution_log: Optional[str] = None
    verification_log: Optional[str] = None
    created_at: datetime
    executed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
