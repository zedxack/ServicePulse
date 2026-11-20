"""
ServicePulse - Direct User Management Endpoints (/api/v1/users)
Provides direct user provisioning and directory listing for Primary Platform Owner,
Platform Super Admins, and Company Administrators.
Author: Muhammadyusuf Usmonov
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import (
    get_current_active_user,
    get_user_tenant_org_id,
    require_roles,
)
from backend.app.db.session import get_db
from backend.app.models.platform_settings import PlatformSettings
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate, UserRead, UserStatusUpdate, UserUpdate
from backend.app.services.auth_service import AuthService

router = APIRouter()


@router.get(
    "",
    response_model=List[UserRead],
    summary="List active registered users directory (tenant-isolated for company admins; global for platform owner)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "admin", "it_admin", "support"))],
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    organization_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[UserRead]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    if scoped_org_id is None and organization_id is not None:
        scoped_org_id = organization_id

    users = await AuthService.list_users(skip, limit, db, scoped_org_id=scoped_org_id)
    ps_res = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    ps = ps_res.scalar_one_or_none()
    owner_id = ps.primary_owner_id if ps else None

    result = []
    for u in users:
        ur = UserRead.model_validate(u)
        ur.is_primary_owner = (owner_id is not None and u.id == owner_id) or (ps is None and u.is_superuser)
        if not ur.organization_name and u.organization:
            ur.organization_name = u.organization.name
        result.append(ur)
    return result


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Directly provision a new user account with login credentials",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "admin"))],
)
async def create_user(
    user_in: UserCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    user = await AuthService.create_user(user_in, current_user, db)
    ps_res = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    ps = ps_res.scalar_one_or_none()
    owner_id = ps.primary_owner_id if ps else None

    ur = UserRead.model_validate(user)
    ur.is_primary_owner = (owner_id is not None and user.id == owner_id)
    if not ur.organization_name and user.organization:
        ur.organization_name = user.organization.name
    return ur


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Retrieve single user record by ID",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "admin"))],
)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    scoped_org_id = get_user_tenant_org_id(current_user)
    user = await AuthService.get_user_by_id(user_id, db, scoped_org_id=scoped_org_id)
    ps_res = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    ps = ps_res.scalar_one_or_none()
    owner_id = ps.primary_owner_id if ps else None

    ur = UserRead.model_validate(user)
    ur.is_primary_owner = (owner_id is not None and user.id == owner_id)
    if not ur.organization_name and user.organization:
        ur.organization_name = user.organization.name
    return ur


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Update user details",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "admin"))],
)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    scoped_org_id = get_user_tenant_org_id(current_user)
    user = await AuthService.update_user(user_id, user_in, current_user, db, scoped_org_id=scoped_org_id)
    ur = UserRead.model_validate(user)
    if not ur.organization_name and user.organization:
        ur.organization_name = user.organization.name
    return ur


@router.patch(
    "/{user_id}/status",
    response_model=UserRead,
    summary="Activate or deactivate user account",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "admin"))],
)
async def update_user_status(
    user_id: int,
    status_in: UserStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    scoped_org_id = get_user_tenant_org_id(current_user)
    user = await AuthService.update_user_status(user_id, status_in.is_active, current_user, db, scoped_org_id=scoped_org_id)
    ur = UserRead.model_validate(user)
    if not ur.organization_name and user.organization:
        ur.organization_name = user.organization.name
    return ur
