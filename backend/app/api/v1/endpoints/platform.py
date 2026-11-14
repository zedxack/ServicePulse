"""
ServicePulse - Platform Administration Endpoints
Super Admin operations for multi-tenant management and onboarding approvals.
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import get_current_active_user, require_roles
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.organization_request import (
    OrganizationRequestRead,
    OrganizationRequestReject,
)
from backend.app.services.organization_request_service import OrganizationRequestService

router = APIRouter(
    dependencies=[Depends(require_roles("platform_super_admin"))]
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
    summary="Approve organization request, create organization and company admin account (Super Admin)",
)
async def approve_organization_request(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationRequestRead:
    return await OrganizationRequestService.approve_request(db, request_id, current_user)


@router.post(
    "/organization-requests/{request_id}/reject",
    response_model=OrganizationRequestRead,
    summary="Reject organization onboarding request (Super Admin)",
)
async def reject_organization_request(
    request_id: int,
    data: Optional[OrganizationRequestReject] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationRequestRead:
    reason = data.reason if data else None
    return await OrganizationRequestService.reject_request(db, request_id, current_user, reason=reason)
