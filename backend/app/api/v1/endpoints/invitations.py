"""
ServicePulse - Direct Invitation Management Endpoints (/api/v1/invitations)
Provides token creation, listing, validation, and revocation for invitations.
Author: Muhammadyusuf Usmonov
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import (
    get_current_active_user,
    require_roles,
)
from backend.app.core.rate_limiter import (
    rate_limit_auth,
    rate_limit_invitation_create,
)
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.invitation import (
    InvitationCreate,
    InvitationCreateResponse,
    InvitationRead,
    InvitationValidateRequest,
    InvitationValidateResponse,
)
from backend.app.services.invitation_service import InvitationService

router = APIRouter()


@router.post(
    "",
    response_model=InvitationCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate time-limited invitation token (Super Admin, Company Admin)",
    dependencies=[
        Depends(require_roles("platform_super_admin", "company_admin")),
        Depends(rate_limit_invitation_create),
    ],
)
async def create_invitation(
    data: InvitationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InvitationCreateResponse:
    invitation, raw_token = await InvitationService.create_invitation(db, current_user, data)
    inv_read = InvitationRead(
        id=invitation.id,
        organization_id=invitation.organization_id,
        organization_name=invitation.organization.name if invitation.organization else None,
        role_id=invitation.role_id,
        role_name=invitation.role.name if invitation.role else None,
        token_prefix=invitation.token_prefix,
        max_uses=invitation.max_uses,
        uses_count=invitation.uses_count,
        expires_at=invitation.expires_at,
        is_revoked=invitation.is_revoked,
        is_valid=invitation.is_valid,
        invited_email=invitation.invited_email,
        created_at=invitation.created_at,
    )
    return InvitationCreateResponse(invitation=inv_read, raw_token=raw_token)


@router.get(
    "",
    response_model=List[InvitationRead],
    summary="List active and historical invitations",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin"))],
)
async def list_invitations(
    organization_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[InvitationRead]:
    invitations = await InvitationService.list_invitations(db, current_user, organization_id=organization_id)
    return [
        InvitationRead(
            id=inv.id,
            organization_id=inv.organization_id,
            organization_name=inv.organization.name if inv.organization else None,
            role_id=inv.role_id,
            role_name=inv.role.name if inv.role else None,
            token_prefix=inv.token_prefix,
            max_uses=inv.max_uses,
            uses_count=inv.uses_count,
            expires_at=inv.expires_at,
            is_revoked=inv.is_revoked,
            is_valid=inv.is_valid,
            invited_email=inv.invited_email,
            created_at=inv.created_at,
        )
        for inv in invitations
    ]


@router.post(
    "/validate",
    response_model=InvitationValidateResponse,
    summary="Validate invitation code status and retrieve associated tenant metadata",
    dependencies=[Depends(rate_limit_auth)],
)
async def validate_invitation(
    req: InvitationValidateRequest,
    db: AsyncSession = Depends(get_db),
) -> InvitationValidateResponse:
    return await InvitationService.validate_invitation(db, req.invitation_code)


@router.delete(
    "/{invitation_id}",
    response_model=InvitationRead,
    summary="Revoke active invitation (Company Admin, Super Admin)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin"))],
)
async def revoke_invitation(
    invitation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InvitationRead:
    inv = await InvitationService.revoke_invitation(db, invitation_id, current_user)
    return InvitationRead(
        id=inv.id,
        organization_id=inv.organization_id,
        organization_name=inv.organization.name if inv.organization else None,
        role_id=inv.role_id,
        role_name=inv.role.name if inv.role else None,
        token_prefix=inv.token_prefix,
        max_uses=inv.max_uses,
        uses_count=inv.uses_count,
        expires_at=inv.expires_at,
        is_revoked=inv.is_revoked,
        is_valid=inv.is_valid,
        invited_email=inv.invited_email,
        created_at=inv.created_at,
    )
