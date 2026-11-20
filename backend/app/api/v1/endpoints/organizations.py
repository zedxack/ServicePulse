"""
ServicePulse - Organization (Tenant) Management Endpoints
Multi-tenant isolation and administrative controls.
Author: Muhammadyusuf Usmonov
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import (
    get_current_active_user,
    is_platform_super_admin,
    require_platform_admin,
    require_tenant_access,
)
from backend.app.db.session import get_db
from backend.app.models.audit import AuditLog
from backend.app.models.organization import Organization
from backend.app.models.user import User
from backend.app.schemas.organization import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)

router = APIRouter()


@router.get(
    "",
    response_model=List[OrganizationRead],
    summary="List all tenant organizations (Platform Super Admin only)",
    dependencies=[Depends(require_platform_admin)]
)
async def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
) -> List[Organization]:
    q = select(Organization).order_by(Organization.id).offset(skip).limit(limit)
    return list((await db.execute(q)).scalars().all())


@router.post(
    "",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant organization (Platform Super Admin only)",
    dependencies=[Depends(require_platform_admin)]
)
async def create_organization(
    org_in: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Organization:
    # Check slug uniqueness
    slug_clean = org_in.slug.strip().lower()
    existing_q = select(Organization).where(Organization.slug == slug_clean)
    if (await db.execute(existing_q)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization with slug '{slug_clean}' already exists"
        )

    org = Organization(
        name=org_in.name.strip(),
        slug=slug_clean,
        domain=org_in.domain.strip() if org_in.domain else None,
        is_active=True,
        max_devices=org_in.max_devices,
    )
    db.add(org)
    await db.flush()

    db.add(AuditLog(
        user_id=current_user.id,
        organization_id=org.id,
        action="organization_created",
        target_resource="organization",
        target_id=str(org.id),
        status="success",
        details=f"Created organization '{org.name}' ({org.slug})",
    ))
    await db.commit()
    await db.refresh(org)
    return org


@router.get(
    "/{org_id}",
    response_model=OrganizationRead,
    summary="Retrieve organization by ID (Super Admin or Tenant Admin)"
)
async def get_organization(
    org_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Organization:
    require_tenant_access(org_id, current_user)
    org_q = select(Organization).where(Organization.id == org_id)
    org = (await db.execute(org_q)).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


@router.patch(
    "/{org_id}",
    response_model=OrganizationRead,
    summary="Update organization details (Super Admin or Tenant Admin)"
)
async def update_organization(
    org_id: int,
    org_in: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Organization:
    require_tenant_access(org_id, current_user)
    org_q = select(Organization).where(Organization.id == org_id)
    org = (await db.execute(org_q)).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    if org_in.name is not None:
        org.name = org_in.name.strip()
    if org_in.domain is not None:
        org.domain = org_in.domain.strip()

    # Only Platform Super Admin can alter activation status or device quota
    if org_in.is_active is not None:
        if not is_platform_super_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Platform Super Administrators can activate or deactivate organizations"
            )
        org.is_active = org_in.is_active

    if org_in.max_devices is not None:
        if not is_platform_super_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Platform Super Administrators can modify organization device quotas"
            )
        org.max_devices = org_in.max_devices

    db.add(org)
    db.add(AuditLog(
        user_id=current_user.id,
        organization_id=org.id,
        action="organization_updated",
        target_resource="organization",
        target_id=str(org.id),
        status="success",
        details=f"Updated organization {org.name}",
    ))
    await db.commit()
    await db.refresh(org)
    return org
