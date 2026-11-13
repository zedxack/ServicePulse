"""
ServicePulse - Five Role-Based Dashboard Schemas
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class BuildingDeviceStatus(BaseModel):
    building_id: int
    building_name: str
    total_devices: int
    online: int
    offline: int
    warning: int


class TelemetrySummary(BaseModel):
    avg_cpu_percent: Optional[float] = None
    avg_ram_percent: Optional[float] = None
    avg_disk_percent: Optional[float] = None
    total_telemetry_records: int


class RiskDevice(BaseModel):
    device_id: int
    name: str
    hostname: str
    device_type: str
    ip_address: str
    incident_count: int
    consecutive_failures: int
    status: str


class IncidentTrendItem(BaseModel):
    date: str
    critical: int
    warning: int
    info: int


class AuditSummaryItem(BaseModel):
    id: int
    action: str
    target_resource: str
    target_id: Optional[str]
    status: str
    created_at: datetime


# 1. PLATFORM SUPER ADMIN DASHBOARD
class PlatformDashboardResponse(BaseModel):
    timestamp: datetime
    total_organizations: int
    active_organizations: int
    inactive_organizations: int
    total_platform_users: int
    total_platform_devices: int
    total_platform_agents: int
    global_active_incidents: int
    platform_health_status: str
    recent_global_audits: List[AuditSummaryItem]


# 2. COMPANY ADMIN DASHBOARD
class CompanyDashboardResponse(BaseModel):
    timestamp: datetime
    organization_id: int
    organization_name: str
    total_users: int
    total_devices: int
    max_devices: int
    device_utilization_percent: float
    total_buildings: int
    active_incidents: int
    recent_org_audits: List[AuditSummaryItem]


# 3. SYSADMIN / IT SUPPORT DASHBOARD
class SysAdminDashboardResponse(BaseModel):
    timestamp: datetime
    organization_id: Optional[int] = None
    total_devices: int
    online_devices: int
    offline_devices: int
    warning_devices: int
    unknown_devices: int
    active_incidents: int
    critical_incidents: int
    daily_incidents: int
    agents_total: int
    agents_active: int
    agents_offline: int
    devices_by_building: List[BuildingDeviceStatus]
    telemetry_summary: TelemetrySummary
    active_outages_count: int = 0
    pending_remediations_count: int = 0
    verified_remediations_count: int = 0
    failed_remediations_count: int = 0
    recent_recoveries_count: int = 0


# 4. CEO / EXECUTIVE DASHBOARD
class CEODashboardResponse(BaseModel):
    timestamp: datetime
    organization_id: Optional[int] = None

    # Contractual SLA Target (Configured agreement target, kept separate from probe checks)
    sla_target_percent: float = 99.5

    # Actual Contractual SLA (Explicitly unavailable until duration-based downtime engine is implemented)
    contractual_sla_uptime_percent: Optional[float] = None
    contractual_sla_status: str = "unavailable"
    contractual_sla_achievement_percent: Optional[float] = None

    # Empirical Probe Success Ratio (Discrete network check probe frequency)
    probe_success_ratio_percent: Optional[float] = None
    probe_success_status: str = "insufficient_data"

    # Real-Time Device Snapshot Availability
    current_device_snapshot_percent: float
    infrastructure_availability_percent: float

    # Legacy / compatibility fields (explicitly None/unavailable to prevent misleading SLA claims)
    measured_historical_sla_uptime_percent: Optional[float] = None
    sla_uptime_status: str = "unavailable"
    sla_achievement_percent: Optional[float] = None
    actual_availability_percent: Optional[float] = None

    # Incident Response Performance (MTTD / MTTR)
    mttd_minutes: Optional[float] = None
    mttr_minutes: Optional[float] = None
    mttd_status: str
    mttr_status: str
    total_incidents_period: int
    active_risk_level: str
    incident_trends: List[IncidentTrendItem]
    top_risk_devices: List[RiskDevice]
    business_impact_summary: Dict[str, str]


# 5. EMPLOYEE DASHBOARD
class EmployeeTicketSummary(BaseModel):
    id: int
    title: str
    priority: str
    status: str
    created_at: datetime


class EmployeeSoftwareSummary(BaseModel):
    id: int
    software_name: str
    status: str
    created_at: datetime


class EmployeeDashboardResponse(BaseModel):
    timestamp: datetime
    user_id: int
    user_name: str
    open_tickets_count: int
    resolved_tickets_count: int
    recent_tickets: List[EmployeeTicketSummary]
    pending_software_requests_count: int
    recent_software_requests: List[EmployeeSoftwareSummary]
