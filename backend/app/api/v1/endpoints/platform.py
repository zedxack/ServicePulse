"""
ServicePulse - Platform Administration Endpoints
Super Admin operations for multi-tenant management and onboarding approvals.
Author: Muhammadyusuf Usmonov
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import (
    require_primary_owner,
    require_roles,
)
from backend.app.db.session import get_db
from backend.app.models.platform_settings import PlatformSettings
from backend.app.models.user import User
from backend.app.schemas.organization_request import (
    OrganizationRequestRead,
    OrganizationRequestReject,
)
from backend.app.services.organization_request_service import OrganizationRequestService

router = APIRouter(
    dependencies=[Depends(require_roles("platform_super_admin"))]
)


class PlatformSettingsRead(BaseModel):
    id: int
    platform_name: str
    primary_owner_id: Optional[int] = None
    allow_public_registration: bool
    bootstrap_completed_at: Optional[str] = None


class PlatformSettingsUpdate(BaseModel):
    allow_public_registration: Optional[bool] = None
    platform_name: Optional[str] = Field(None, max_length=100)


@router.get(
    "/settings",
    response_model=PlatformSettingsRead,
    summary="Get platform configuration settings (Super Admin)",
)
async def get_platform_settings(
    db: AsyncSession = Depends(get_db),
) -> PlatformSettingsRead:
    res = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    ps = res.scalar_one_or_none()
    if not ps:
        return PlatformSettingsRead(
            id=1,
            platform_name="ServicePulse",
            primary_owner_id=None,
            allow_public_registration=True,
            bootstrap_completed_at=None,
        )
    return PlatformSettingsRead(
        id=ps.id,
        platform_name=ps.platform_name,
        primary_owner_id=ps.primary_owner_id,
        allow_public_registration=ps.allow_public_registration,
        bootstrap_completed_at=ps.bootstrap_completed_at.isoformat() if ps.bootstrap_completed_at else None,
    )


@router.patch(
    "/settings",
    response_model=PlatformSettingsRead,
    summary="Update platform settings (Primary Platform Owner)",
)
async def update_platform_settings(
    update_data: PlatformSettingsUpdate,
    current_owner: User = Depends(require_primary_owner),
    db: AsyncSession = Depends(get_db),
) -> PlatformSettingsRead:
    res = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    ps = res.scalar_one_or_none()
    if not ps:
        ps = PlatformSettings(id=1, primary_owner_id=current_owner.id)
        db.add(ps)
        await db.flush()

    if update_data.allow_public_registration is not None:
        ps.allow_public_registration = update_data.allow_public_registration
    if update_data.platform_name is not None:
        ps.platform_name = update_data.platform_name.strip()

    db.add(ps)
    await db.commit()
    await db.refresh(ps)

    return PlatformSettingsRead(
        id=ps.id,
        platform_name=ps.platform_name,
        primary_owner_id=ps.primary_owner_id,
        allow_public_registration=ps.allow_public_registration,
        bootstrap_completed_at=ps.bootstrap_completed_at.isoformat() if ps.bootstrap_completed_at else None,
    )


@router.get(
    "/organization-requests",
    response_model=List[OrganizationRequestRead],
    summary="List all organization onboarding requests (Super Admin)",
)
async def list_organization_requests(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (pending, approved, rejected)"),
    db: AsyncSession = Depends(get_db),
) -> List[OrganizationRequestRead]:
    return await OrganizationRequestService.list_requests(db, status_filter=status_filter)


@router.get(
    "/organization-requests/{request_id}",
    response_model=OrganizationRequestRead,
    summary="Get details of a specific organization onboarding request (Super Admin)",
)
async def get_organization_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
) -> OrganizationRequestRead:
    return await OrganizationRequestService.get_request(db, request_id)


@router.post(
    "/organization-requests/{request_id}/approve",
    response_model=OrganizationRequestRead,
    summary="Approve organization request (Primary Platform Owner only)",
)
async def approve_organization_request(
    request_id: int,
    current_owner: User = Depends(require_primary_owner),
    db: AsyncSession = Depends(get_db),
) -> OrganizationRequestRead:
    return await OrganizationRequestService.approve_request(db, request_id, current_owner)


@router.post(
    "/organization-requests/{request_id}/reject",
    response_model=OrganizationRequestRead,
    summary="Reject organization onboarding request (Primary Platform Owner only)",
)
async def reject_organization_request(
    request_id: int,
    data: OrganizationRequestReject,
    current_owner: User = Depends(require_primary_owner),
    db: AsyncSession = Depends(get_db),
) -> OrganizationRequestRead:
    if not data.reason or len(data.reason.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A non-empty rejection reason (at least 3 characters) is required."
        )
    return await OrganizationRequestService.reject_request(db, request_id, current_owner, reason=data.reason.strip())
