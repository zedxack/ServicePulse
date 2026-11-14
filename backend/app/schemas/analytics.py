"""
ServicePulse - Analytics & SLA Schemas
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class SLAOverviewResponse(BaseModel):
    sla_target_percent: float
    measured_uptime_percent: Optional[float]
    is_sla_met: Optional[bool]
    uptime_status: str
    data_completeness: str
    observation_window_days: int
    period_start: datetime
    period_end: datetime
    total_monitored_devices: int
    total_downtime_minutes: float
    eligible_duration_minutes: float
    excluded_maintenance_minutes: float
    total_outages: int
    mttd_minutes: Optional[float] = None
    mttr_minutes: Optional[float] = None


class AvailabilityTrendPoint(BaseModel):
    date: str
    uptime_percent: Optional[float]
    downtime_minutes: float
    is_complete: bool


class AvailabilityTrendResponse(BaseModel):
    points: List[AvailabilityTrendPoint]


class IncidentTrendPoint(BaseModel):
    date: str
    critical_count: int
    warning_count: int
    info_count: int
    resolved_count: int


class IncidentTrendResponse(BaseModel):
    total_incidents: int
    points: List[IncidentTrendPoint]
