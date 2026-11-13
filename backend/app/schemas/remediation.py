"""
ServicePulse - Automated Remediation Schemas
Allowlisted action definitions, parameter schemas, execution tracking, and approvals.
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# Allowlisted Action Parameter Schemas (strictly typed, preventing shell injection)
class RestartServiceParams(BaseModel):
    service_name: str = Field("ServicePulseAgent", max_length=100, pattern=r"^[a-zA-Z0-9_\-\. ]+$")
    timeout_seconds: int = Field(30, ge=5, le=120)


class RestartAgentParams(BaseModel):
    timeout_seconds: int = Field(30, ge=5, le=120)


class RunDiagnosticParams(BaseModel):
    diagnostic_type: str = Field("network_summary", pattern=r"^(network_summary|service_status|disk_health)$")
    include_event_logs: bool = False


class RecheckNetworkParams(BaseModel):
    port: Optional[int] = Field(None, ge=1, le=65535)
    timeout_seconds: float = Field(3.0, ge=0.5, le=30.0)


class NotifyAdminParams(BaseModel):
    channel: str = Field("dashboard", pattern=r"^(dashboard|email|sms)$")
    message: str = Field("Automated alert from ServicePulse Remediation Engine", max_length=500)


class RemediationRuleCreate(BaseModel):
    name: str = Field(..., max_length=150)
    description: Optional[str] = None
    trigger_condition: str = Field(..., max_length=100)
    target_device_type: Optional[str] = "workstation"
    action_name: str = Field(
        ...,
        description="One of: restart_service, restart_servicepulse_agent, run_diagnostic_check, recheck_network_endpoint, notify_administrator"
    )
    action_parameters: Optional[str] = None
    is_active: bool = True
    requires_approval: bool = False
    max_retries: int = Field(2, ge=0, le=5)
    cooldown_seconds: int = Field(300, ge=30, le=86400)


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
    max_retries: int
    cooldown_seconds: int
    created_at: datetime


class RemediationExecutionCreate(BaseModel):
    rule_id: int
    incident_id: int
    device_id: Optional[int] = None
    is_simulation: bool = False


class RemediationApprovalRequest(BaseModel):
    decision: str = Field(..., pattern=r"^(approved|rejected)$")
    review_notes: Optional[str] = None


class RemediationExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_id: int
    incident_id: int
    device_id: Optional[int] = None
    agent_command_id: Optional[int] = None
    status: str
    verification_status: str
    is_simulation: bool = False
    retry_count: int = 0
    approved_by_user_id: Optional[int] = None
    execution_log: Optional[str] = None
    verification_log: Optional[str] = None
    created_at: datetime
    executed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
