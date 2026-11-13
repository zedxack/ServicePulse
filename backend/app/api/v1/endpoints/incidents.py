"""
ServicePulse - Incident Management Endpoints
Concurrency-safe deduplication, incident lifecycle & audit trail
Multi-tenant isolation enforced.
Author: Muhammadyusuf Usmonov
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import (
    get_current_active_user,
    get_user_tenant_org_id,
    require_roles,
)
from backend.app.db.session import get_db
from backend.app.models.incident import Incident
from backend.app.models.user import User
from backend.app.schemas.incident import (
    IncidentAcknowledge,
    IncidentAssign,
    IncidentCreate,
    IncidentListResponse,
    IncidentRead,
    IncidentResolve,
)
from backend.app.services.incident_service import IncidentService

router = APIRouter()

INCIDENT_RESPONDERS = ("platform_super_admin", "company_admin", "it_admin", "support", "admin")


@router.get(
    "",
    response_model=IncidentListResponse,
    summary="List incidents with filtering and pagination",
)
async def list_incidents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    severity: Optional[str] = Query(None, description="Filter by critical, warning, info"),
    status_val: Optional[str] = Query(None, alias="status", description="Filter by open, acknowledged, in_progress, resolved"),
    device_id: Optional[int] = Query(None, description="Filter by associated device ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> IncidentListResponse:
    scoped_org_id = get_user_tenant_org_id(current_user)
    total, items = await IncidentService.list_incidents(
        skip, limit, severity, status_val, device_id, db, scoped_org_id=scoped_org_id
    )
    return IncidentListResponse(total=total, items=items)


@router.post(
    "",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create or concurrency-safely deduplicate an incident"
)
async def create_incident(
    inc_in: IncidentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Incident:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await IncidentService.create_or_deduplicate_incident(inc_in, current_user, db, scoped_org_id=scoped_org_id)


@router.get(
    "/{incident_id}",
    response_model=IncidentRead,
    summary="Retrieve incident by ID with full event audit history",
)
async def get_incident(
    incident_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Incident:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await IncidentService.get_incident_by_id(incident_id, db, scoped_org_id=scoped_org_id)


@router.patch(
    "/{incident_id}/assign",
    response_model=IncidentRead,
    summary="Assign incident to a technician",
    dependencies=[Depends(require_roles(*INCIDENT_RESPONDERS))]
)
async def assign_incident(
    incident_id: int,
    assign_in: IncidentAssign,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Incident:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await IncidentService.assign_incident(incident_id, assign_in, current_user, db, scoped_org_id=scoped_org_id)


@router.patch(
    "/{incident_id}/acknowledge",
    response_model=IncidentRead,
    summary="Acknowledge active incident",
    dependencies=[Depends(require_roles(*INCIDENT_RESPONDERS))]
)
async def acknowledge_incident(
    incident_id: int,
    ack_in: IncidentAcknowledge,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Incident:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await IncidentService.acknowledge_incident(incident_id, ack_in, current_user, db, scoped_org_id=scoped_org_id)


@router.patch(
    "/{incident_id}/resolve",
    response_model=IncidentRead,
    summary="Resolve incident and clear active deduplication key",
    dependencies=[Depends(require_roles(*INCIDENT_RESPONDERS))]
)
async def resolve_incident(
    incident_id: int,
    res_in: IncidentResolve,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Incident:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await IncidentService.resolve_incident(incident_id, res_in, current_user, db, scoped_org_id=scoped_org_id)
