"""
ServicePulse - Agent & Telemetry Pydantic Schemas
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentEnrollRequest(BaseModel):
    enrollment_secret: str = Field(..., description="Global enrollment secret key")
    hostname: str = Field(..., max_length=150)
    ip_address: str = Field(..., max_length=45)
    os_name: Optional[str] = Field(None, max_length=100)
    version: str = Field("1.0.0", max_length=30)
    device_id: Optional[int] = Field(None, description="Optional pre-existing device ID to bind to")
    organization_id: Optional[int] = Field(None, description="Optional organization ID for tenant isolation")


class AgentEnrollResponse(BaseModel):
    agent_uuid: str
    api_token: str = Field(..., description="Bearer token for agent authentication (store securely on host)")
    device_id: Optional[int]
    organization_id: Optional[int] = None
    status: str
    message: str


class AgentHeartbeatRequest(BaseModel):
    agent_version: Optional[str] = Field(None, max_length=30)
    ip_address: Optional[str] = Field(None, max_length=45)


class AgentHeartbeatResponse(BaseModel):
    status: str
    server_time: datetime
    acknowledged: bool = True


class AgentTelemetryRequest(BaseModel):
    cpu_percent: float = Field(..., ge=0.0, le=100.0)
    ram_percent: float = Field(..., ge=0.0, le=100.0)
    ram_used_mb: float = Field(..., ge=0.0)
    ram_total_mb: float = Field(..., ge=0.0)
    disk_percent: float = Field(..., ge=0.0, le=100.0)
    disk_used_gb: float = Field(..., ge=0.0)
    disk_total_gb: float = Field(..., ge=0.0)
    windows_activation_status: Optional[str] = Field(None, max_length=50)
    windows_defender_status: Optional[str] = Field(None, max_length=50)
    recorded_at: Optional[datetime] = None
    idempotency_key: Optional[str] = Field(None, max_length=128, description="Unique client-generated transmission key")


class AgentTelemetryResponse(BaseModel):
    status: str
    telemetry_id: int
    is_duplicate: bool = False
    message: str


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: Optional[int] = None
    device_id: Optional[int] = None
    agent_uuid: str
    status: str
    version: str
    hostname: str
    ip_address: str
    os_name: Optional[str] = None
    last_seen: Optional[datetime] = None
    created_at: datetime


class AgentTelemetryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    cpu_percent: float
    ram_percent: float
    ram_used_mb: float
    ram_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    windows_activation_status: Optional[str] = None
    windows_defender_status: Optional[str] = None
    recorded_at: datetime
    created_at: datetime


class AgentCommandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    device_id: Optional[int] = None
    action_name: str
    parameters: Optional[str] = None
    status: str
    verification_status: str
    execution_result: Optional[str] = None
    verification_result: Optional[str] = None
    requested_by_user_id: Optional[int] = None
    executed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    created_at: datetime


class AgentCommandAckResponse(BaseModel):
    command_id: int
    status: str = "acknowledged"
    message: str = "Command successfully acknowledged by agent"


class AgentCommandResultRequest(BaseModel):
    status: str = Field(..., max_length=30, description="Status: succeeded, failed, or executing")
    execution_result: Optional[str] = Field(None, description="Execution output log or details")
    executed_at: Optional[datetime] = None


class AgentCommandResultResponse(BaseModel):
    command_id: int
    status: str
    message: str


class AgentBootstrapConfigResponse(BaseModel):
    server_url: str
    organization_id: int
    organization_name: str
    enrollment_secret_masked: str
    powershell_command: str
    linux_bash_command: str
    manual_steps: List[str]
    agent_version: str = "1.0.0"

