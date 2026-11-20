"""
ServicePulse - Access Requests Endpoints
Centralized Access Governance approval workflows.
Author: Muhammadyusuf Usmonov
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import (
    get_current_active_user,
    require_primary_owner,
    require_roles,
)
from backend.app.core.rate_limiter import get_client_ip
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.access_request import (
    AccessRequestCreate,
    AccessRequestRead,
    AccessRequestReject,
    AccessRequestStats,
)
from backend.app.services.access_request_service import AccessRequestService

router = APIRouter()


@router.get(
    "",
    response_model=List[AccessRequestRead],
    summary="List access requests (Platform Admins see all, Company Admins see organization requests)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin"))],
)
async def list_access_requests(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (pending, approved, rejected)"),
    type_filter: Optional[str] = Query(None, alias="type", description="Filter by request type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[AccessRequestRead]:
    return await AccessRequestService.list_requests(
        db=db,
        current_user=current_user,
        status_filter=status_filter,
        type_filter=type_filter,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/stats",
    response_model=AccessRequestStats,
    summary="Get access request counts (Pending, Approved, Rejected)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin"))],
)
async def get_access_request_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> AccessRequestStats:
    return await AccessRequestService.get_stats(db, current_user)


@router.get(
    "/{request_id}",
    response_model=AccessRequestRead,
    summary="Get details of a specific access request",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin"))],
)
async def get_access_request(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> AccessRequestRead:
    return await AccessRequestService.get_request(db, request_id, current_user)


@router.post(
    "",
    response_model=AccessRequestRead,
    summary="Submit an access request (Company Admins or Super Admins)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin"))],
)
async def create_access_request(
    data: AccessRequestCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> AccessRequestRead:
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    return await AccessRequestService.submit_access_request(
        db=db,
        data=data,
        requester=current_user,
        client_ip=client_ip,
        user_agent=user_agent,
    )


@router.post(
    "/{request_id}/approve",
    response_model=AccessRequestRead,
    summary="Approve access request (Primary Platform Owner only)",
)
async def approve_access_request(
    request_id: int,
    current_owner: User = Depends(require_primary_owner),
    db: AsyncSession = Depends(get_db),
) -> AccessRequestRead:
    return await AccessRequestService.approve_request(db, request_id, current_owner)


@router.post(
    "/{request_id}/reject",
    response_model=AccessRequestRead,
    summary="Reject access request with mandatory reason (Primary Platform Owner only)",
)
async def reject_access_request(
    request_id: int,
    data: AccessRequestReject,
    current_owner: User = Depends(require_primary_owner),
    db: AsyncSession = Depends(get_db),
) -> AccessRequestRead:
    return await AccessRequestService.reject_request(db, request_id, current_owner, reason=data.reason)
