"""
ServicePulse - Helpdesk Ticket Endpoints
Employee isolation, ticket lifecycle & comments
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
from backend.app.models.ticket import Ticket, TicketComment
from backend.app.models.user import User
from backend.app.schemas.ticket import (
    TicketAssign,
    TicketCommentCreate,
    TicketCommentRead,
    TicketCreate,
    TicketRead,
    TicketResolve,
    TicketUpdate,
)
from backend.app.services.ticket_service import TicketService

router = APIRouter()

TICKET_RESPONDERS = ("platform_super_admin", "company_admin", "it_admin", "support", "admin")


@router.post(
    "",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new IT support ticket"
)
async def create_ticket(
    ticket_in: TicketCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Ticket:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await TicketService.create_ticket(ticket_in, current_user, db, scoped_org_id=scoped_org_id)


@router.get(
    "",
    response_model=List[TicketRead],
    summary="List tickets (Employees see their own; Support/Admin see org tickets)"
)
async def list_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    status_val: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[Ticket]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await TicketService.list_tickets(
        current_user, skip, limit, status_val, priority, db, scoped_org_id=scoped_org_id
    )


@router.get(
    "/{ticket_id}",
    response_model=TicketRead,
    summary="Retrieve ticket by ID with discussion comments"
)
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Ticket:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await TicketService.get_ticket_by_id(ticket_id, current_user, db, scoped_org_id=scoped_org_id)


@router.patch(
    "/{ticket_id}",
    response_model=TicketRead,
    summary="Update ticket metadata"
)
async def update_ticket(
    ticket_id: int,
    ticket_in: TicketUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Ticket:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await TicketService.update_ticket(ticket_id, ticket_in, current_user, db, scoped_org_id=scoped_org_id)


@router.post(
    "/{ticket_id}/comments",
    response_model=TicketCommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment to a ticket thread"
)
async def add_ticket_comment(
    ticket_id: int,
    comment_in: TicketCommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> TicketComment:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await TicketService.add_comment(ticket_id, comment_in, current_user, db, scoped_org_id=scoped_org_id)


@router.get(
    "/{ticket_id}/comments",
    response_model=List[TicketCommentRead],
    summary="Retrieve comments for a ticket thread (tenant-scoped)"
)
async def get_ticket_comments(
    ticket_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[TicketComment]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    ticket = await TicketService.get_ticket_by_id(ticket_id, current_user, db, scoped_org_id=scoped_org_id)
    return ticket.comments


@router.patch(
    "/{ticket_id}/assign",
    response_model=TicketRead,
    summary="Assign ticket to a support technician",
    dependencies=[Depends(require_roles(*TICKET_RESPONDERS))]
)
async def assign_ticket(
    ticket_id: int,
    assign_in: TicketAssign,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Ticket:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await TicketService.assign_ticket(ticket_id, assign_in, current_user, db, scoped_org_id=scoped_org_id)


@router.patch(
    "/{ticket_id}/resolve",
    response_model=TicketRead,
    summary="Mark ticket as resolved",
    dependencies=[Depends(require_roles(*TICKET_RESPONDERS))]
)
async def resolve_ticket(
    ticket_id: int,
    res_in: TicketResolve,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Ticket:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await TicketService.resolve_ticket(ticket_id, res_in, current_user, db, scoped_org_id=scoped_org_id)
