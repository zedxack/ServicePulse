"""
ServicePulse - Network Monitoring API Endpoints
Probe execution, network check history, device status, and maintenance windows.
Multi-tenant isolation and strict RBAC authorization enforced.
Author: Muhammadyusuf Usmonov
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import (
    get_current_active_user,
    get_user_tenant_org_id,
    require_roles,
)
from backend.app.db.session import get_db
from backend.app.models.monitoring import MaintenanceWindow
from backend.app.models.network import NetworkCheck
from backend.app.models.user import User
from backend.app.schemas.monitoring import (
    DeviceStatusResponse,
    MaintenanceWindowCreate,
    MaintenanceWindowRead,
    NetworkHealthResponse,
    ProbeRequest,
    ProbeResult,
)
from backend.app.schemas.network import NetworkCheckRead
from backend.app.services.network_service import NetworkService

router = APIRouter()

# Role groups
MONITORING_VIEWERS = ("platform_super_admin", "company_admin", "it_admin", "support", "executive", "admin")
PROBE_OPERATORS = ("platform_super_admin", "company_admin", "it_admin", "support", "admin")
MAINTENANCE_MANAGERS = ("platform_super_admin", "company_admin", "it_admin", "admin")


@router.get(
    "/checks",
    response_model=List[NetworkCheckRead],
    summary="List network check history (tenant-scoped)",
    dependencies=[Depends(require_roles(*MONITORING_VIEWERS))]
)
async def list_network_checks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    device_id: Optional[int] = Query(None, description="Filter by device ID"),
    check_type: Optional[str] = Query(None, description="Filter by check type: icmp_ping, tcp_port"),
    is_successful: Optional[bool] = Query(None, description="Filter by success/failure"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[NetworkCheck]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await NetworkService.list_checks(
        skip=skip,
        limit=limit,
        device_id=device_id,
        check_type=check_type,
        is_successful=is_successful,
        scoped_org_id=scoped_org_id,
        db=db,
    )


@router.get(
    "/devices/{device_id}/checks",
    response_model=List[NetworkCheckRead],
    summary="Get network checks for a specific device (tenant-scoped)",
    dependencies=[Depends(require_roles(*MONITORING_VIEWERS))]
)
async def get_device_network_checks(
    device_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[NetworkCheck]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await NetworkService.get_device_checks(
        device_id=device_id,
        skip=skip,
        limit=limit,
        scoped_org_id=scoped_org_id,
        db=db,
    )


@router.post(
    "/devices/{device_id}/probe",
    response_model=ProbeResult,
    summary="Trigger an on-demand network probe for an authorized device",
    dependencies=[Depends(require_roles(*PROBE_OPERATORS))]
)
async def trigger_device_probe(
    device_id: int,
    probe_in: ProbeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ProbeResult:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await NetworkService.trigger_on_demand_probe(
        device_id=device_id,
        probe_req=probe_in,
        scoped_org_id=scoped_org_id,
        db=db,
    )


@router.get(
    "/devices/{device_id}/status",
    response_model=DeviceStatusResponse,
    summary="Get live monitoring status, outage state, and failure counts for a device",
    dependencies=[Depends(require_roles(*MONITORING_VIEWERS))]
)
async def get_device_monitoring_status(
    device_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> DeviceStatusResponse:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await NetworkService.get_device_status(
        device_id=device_id,
        scoped_org_id=scoped_org_id,
        db=db,
    )


@router.get(
    "/health",
    response_model=NetworkHealthResponse,
    summary="Network monitoring subsystem health and active outage metrics",
    dependencies=[Depends(require_roles(*MONITORING_VIEWERS))]
)
async def get_network_monitoring_health(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> NetworkHealthResponse:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await NetworkService.get_network_health(
        scoped_org_id=scoped_org_id,
        db=db,
    )


@router.post(
    "/maintenance",
    response_model=MaintenanceWindowRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create scheduled maintenance window (tenant-scoped)",
    dependencies=[Depends(require_roles(*MAINTENANCE_MANAGERS))]
)
async def create_maintenance_window(
    m_in: MaintenanceWindowCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> MaintenanceWindow:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await NetworkService.create_maintenance_window(
        m_in=m_in,
        user=current_user,
        scoped_org_id=scoped_org_id,
        db=db,
    )


@router.get(
    "/maintenance",
    response_model=List[MaintenanceWindowRead],
    summary="List scheduled maintenance windows (tenant-scoped)",
    dependencies=[Depends(require_roles(*MONITORING_VIEWERS))]
)
async def list_maintenance_windows(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[MaintenanceWindow]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await NetworkService.list_maintenance_windows(
        scoped_org_id=scoped_org_id,
        db=db,
    )
