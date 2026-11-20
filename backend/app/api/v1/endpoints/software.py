"""
ServicePulse - Software Installation Approval Workflow Endpoints
Multi-tenant isolation enforced.
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
from backend.app.models.ticket import SoftwareRequest
from backend.app.models.user import User
from backend.app.schemas.ticket import (
    SoftwareRequestCreate,
    SoftwareRequestRead,
    SoftwareRequestReview,
)
from backend.app.services.ticket_service import TicketService

router = APIRouter()

SOFTWARE_APPROVERS = ("platform_super_admin", "company_admin", "admin", "it_admin")


@router.get(
    "/catalog",
    response_model=List[str],
    summary="List approved enterprise software packages available for installation",
    dependencies=[Depends(get_current_active_user)]
)
async def get_software_catalog() -> List[str]:
    from backend.app.core.config import settings
    return settings.APPROVED_SOFTWARE_CATALOG


@router.post(
    "/requests",
    response_model=SoftwareRequestRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a software installation request"
)
async def submit_software_request(
    req_in: SoftwareRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> SoftwareRequest:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await TicketService.create_software_request(req_in, current_user, db, scoped_org_id=scoped_org_id)


@router.get(
    "/requests",
    response_model=List[SoftwareRequestRead],
    summary="List software installation requests"
)
async def list_software_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    status_val: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[SoftwareRequest]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await TicketService.list_software_requests(
        current_user, skip, limit, status_val, db, scoped_org_id=scoped_org_id
    )


@router.get(
    "/requests/{request_id}",
    response_model=SoftwareRequestRead,
    summary="Get software request details"
)
async def get_software_request(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> SoftwareRequest:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await TicketService.get_software_request_by_id(
        request_id, current_user, db, scoped_org_id=scoped_org_id
    )


@router.post(
    "/requests/{request_id}/approve",
    response_model=SoftwareRequestRead,
    summary="Approve software installation request",
    dependencies=[Depends(require_roles(*SOFTWARE_APPROVERS))]
)
async def approve_software_request(
    request_id: int,
    review_in: SoftwareRequestReview,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> SoftwareRequest:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await TicketService.approve_software_request(
        request_id, review_in, current_user, db, scoped_org_id=scoped_org_id
    )


@router.post(
    "/requests/{request_id}/reject",
    response_model=SoftwareRequestRead,
    summary="Reject software installation request",
    dependencies=[Depends(require_roles(*SOFTWARE_APPROVERS))]
)
async def reject_software_request(
    request_id: int,
    review_in: SoftwareRequestReview,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> SoftwareRequest:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await TicketService.reject_software_request(
        request_id, review_in, current_user, db, scoped_org_id=scoped_org_id
    )
