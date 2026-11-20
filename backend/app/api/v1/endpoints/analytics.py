"""
ServicePulse - Analytics & SLA Endpoints
Author: Muhammadyusuf Usmonov
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import get_current_active_user, get_user_tenant_org_id
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.analytics import (
    AvailabilityTrendResponse,
    IncidentTrendResponse,
    SLAOverviewResponse,
)
from backend.app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get(
    "/sla",
    response_model=SLAOverviewResponse,
    summary="Get duration-based historical SLA & availability overview",
)
async def get_sla_overview(
    days: Optional[int] = Query(None, ge=1, le=365, description="Observation window in days (7, 30, 90)"),
    period_days: Optional[int] = Query(None, ge=1, le=365, description="Alias for days"),
    device_id: Optional[int] = Query(None, description="Optional target device ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SLAOverviewResponse:
    scoped_org_id = get_user_tenant_org_id(current_user)
    target_org = scoped_org_id or current_user.organization_id or 1
    selected_days = period_days or days or 30
    return await AnalyticsService.get_sla_overview(
        org_id=target_org,
        days=selected_days,
        device_id=device_id,
        db=db,
    )


@router.get(
    "/availability-trend",
    response_model=AvailabilityTrendResponse,
    summary="Get day-by-day availability trend with data completeness indicators",
)
async def get_availability_trend(
    days: Optional[int] = Query(None, ge=1, le=90, description="Trend duration in days"),
    period_days: Optional[int] = Query(None, ge=1, le=90, description="Alias for days"),
    device_id: Optional[int] = Query(None, description="Optional target device ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> AvailabilityTrendResponse:
    scoped_org_id = get_user_tenant_org_id(current_user)
    target_org = scoped_org_id or current_user.organization_id or 1
    selected_days = period_days or days or 14
    return await AnalyticsService.get_availability_trend(
        org_id=target_org,
        days=selected_days,
        device_id=device_id,
        db=db,
    )


@router.get(
    "/incident-trends",
    response_model=IncidentTrendResponse,
    summary="Get incident frequency and severity distribution trends",
)
async def get_incident_trends(
    days: Optional[int] = Query(None, ge=1, le=90, description="Trend duration in days"),
    period_days: Optional[int] = Query(None, ge=1, le=90, description="Alias for days"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> IncidentTrendResponse:
    scoped_org_id = get_user_tenant_org_id(current_user)
    target_org = scoped_org_id or current_user.organization_id or 1
    selected_days = period_days or days or 14
    return await AnalyticsService.get_incident_trends(
        org_id=target_org,
        days=selected_days,
        db=db,
    )
