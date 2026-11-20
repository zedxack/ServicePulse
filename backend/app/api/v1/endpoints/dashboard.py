"""
ServicePulse - Five Role-Based Dashboard Endpoints
1. Platform Super Admin (/platform)
2. Company Admin (/company)
3. SysAdmin / IT Support (/sysadmin)
4. Executive / CEO (/executive and /ceo)
5. Employee Self-Service (/employee)
Author: Muhammadyusuf Usmonov
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import (
    get_current_active_user,
    get_user_tenant_org_id,
    require_platform_admin,
    require_roles,
)
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.dashboard import (
    CEODashboardResponse,
    CompanyDashboardResponse,
    EmployeeDashboardResponse,
    PlatformDashboardResponse,
    SysAdminDashboardResponse,
)
from backend.app.services.dashboard_service import DashboardService

router = APIRouter()


# -----------------------------------------------------------------------------
# 1. PLATFORM SUPER ADMIN DASHBOARD
# -----------------------------------------------------------------------------
@router.get(
    "/platform",
    response_model=PlatformDashboardResponse,
    summary="Platform Super Admin global tenant & health dashboard",
    dependencies=[Depends(require_platform_admin)]
)
async def get_platform_dashboard(
    db: AsyncSession = Depends(get_db)
) -> PlatformDashboardResponse:
    return await DashboardService.get_platform_dashboard(db)


# -----------------------------------------------------------------------------
# 2. COMPANY ADMIN DASHBOARD
# -----------------------------------------------------------------------------
@router.get(
    "/company",
    response_model=CompanyDashboardResponse,
    summary="Company Admin organizational capacity & user/device overview",
    dependencies=[Depends(require_roles("company_admin", "admin", "platform_super_admin"))]
)
async def get_company_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> CompanyDashboardResponse:
    org_id = current_user.organization_id
    if not org_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )
    # If superuser without assigned org, default to org 1
    target_org_id = org_id or 1
    return await DashboardService.get_company_dashboard(target_org_id, db)


# -----------------------------------------------------------------------------
# 3. SYSADMIN / IT SUPPORT DASHBOARD
# -----------------------------------------------------------------------------
@router.get(
    "/sysadmin",
    response_model=SysAdminDashboardResponse,
    summary="SysAdmin operations telemetry, active alerts & infrastructure health",
    dependencies=[Depends(require_roles("it_admin", "support", "admin", "company_admin", "platform_super_admin"))]
)
async def get_sysadmin_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> SysAdminDashboardResponse:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await DashboardService.get_sysadmin_dashboard(db, scoped_org_id=scoped_org_id)


# -----------------------------------------------------------------------------
# 4. CEO / EXECUTIVE DASHBOARD
# -----------------------------------------------------------------------------
@router.get(
    "/executive",
    response_model=CEODashboardResponse,
    summary="Executive summary: infrastructure availability, SLA, MTTD, MTTR & risk endpoints",
    dependencies=[Depends(require_roles("executive", "platform_super_admin", "company_admin", "admin", "it_admin"))]
)
async def get_executive_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> CEODashboardResponse:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await DashboardService.get_ceo_dashboard(db, scoped_org_id=scoped_org_id)


@router.get(
    "/ceo",
    response_model=CEODashboardResponse,
    summary="Alias for /executive dashboard",
    dependencies=[Depends(require_roles("executive", "platform_super_admin", "company_admin", "admin", "it_admin"))]
)
async def get_ceo_dashboard_alias(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> CEODashboardResponse:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await DashboardService.get_ceo_dashboard(db, scoped_org_id=scoped_org_id)


# -----------------------------------------------------------------------------
# 5. EMPLOYEE DASHBOARD
# -----------------------------------------------------------------------------
@router.get(
    "/employee",
    response_model=EmployeeDashboardResponse,
    summary="Employee self-service dashboard: tickets and software requests",
)
async def get_employee_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> EmployeeDashboardResponse:
    return await DashboardService.get_employee_dashboard(current_user, db)
