"""
ServicePulse - Network Monitoring Schemas
Pydantic validation models for probes, configurations, device status, and maintenance.
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DeviceMonitoringConfigBase(BaseModel):
    is_enabled: bool = True
    is_authorized: bool = True
    ping_enabled: bool = True
    tcp_ports: Optional[str] = "80,443,554,8291"
    check_interval_seconds: int = Field(30, ge=5, le=3600)
    timeout_seconds: float = Field(3.0, ge=0.5, le=30.0)
    consecutive_failure_threshold: int = Field(3, ge=1, le=10)
    simulation_mode: bool = False


class DeviceMonitoringConfigUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    is_authorized: Optional[bool] = None
    ping_enabled: Optional[bool] = None
    tcp_ports: Optional[str] = None
    check_interval_seconds: Optional[int] = Field(None, ge=5, le=3600)
    timeout_seconds: Optional[float] = Field(None, ge=0.5, le=30.0)
    consecutive_failure_threshold: Optional[int] = Field(None, ge=1, le=10)
    simulation_mode: Optional[bool] = None


class DeviceMonitoringConfigRead(DeviceMonitoringConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    created_at: datetime
    updated_at: datetime


class ProbeRequest(BaseModel):
    check_type: str = Field("icmp_ping", description="icmp_ping or tcp_port")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Port required if check_type is tcp_port")


class ProbeResult(BaseModel):
    device_id: int
    target_ip: str
    check_type: str
    port: Optional[int] = None
    is_successful: bool
    response_time_ms: float
    packet_loss_percent: float
    error_message: Optional[str] = None
    is_simulated: bool = False
    checked_at: datetime


class DeviceStatusResponse(BaseModel):
    device_id: int
    organization_id: Optional[int] = None
    name: str
    hostname: str
    ip_address: str
    device_type: str
    status: str
    consecutive_failures: int
    last_seen: Optional[datetime] = None
    last_attempted_check: Optional[datetime] = None
    last_successful_check: Optional[datetime] = None
    is_monitored: bool
    is_authorized: bool
    active_outage: bool = False
    monitoring_config: Optional[DeviceMonitoringConfigRead] = None


class NetworkHealthResponse(BaseModel):
    worker_status: str
    active_monitored_devices: int
    total_probes_recorded: int
    recent_failures_count: int
    active_outages_count: int
    timestamp: datetime


class OutageIntervalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: Optional[int] = None
    device_id: int
    incident_id: Optional[int] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    is_planned: bool
    root_cause: Optional[str] = None


class MaintenanceWindowCreate(BaseModel):
    title: str = Field(..., max_length=150)
    description: Optional[str] = None
    device_id: Optional[int] = None
    start_time: datetime
    end_time: datetime


class MaintenanceWindowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    title: str
    description: Optional[str] = None
    device_id: Optional[int] = None
    start_time: datetime
    end_time: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime
