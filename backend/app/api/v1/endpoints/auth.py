"""
ServicePulse - Authentication & User Management Endpoints
Author: Muhammadyusuf Usmonov
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.dependencies import (
    get_current_active_user,
    get_user_tenant_org_id,
    require_roles,
)
from backend.app.core.rate_limiter import (
    get_client_ip,
    rate_limit_auth,
    rate_limit_invitation_create,
    rate_limit_registration,
)
from backend.app.db.session import get_db
from backend.app.models.platform_settings import PlatformSettings
from backend.app.models.user import Role, User
from backend.app.schemas.invitation import (
    InvitationCreate,
    InvitationCreateResponse,
    InvitationRead,
    InvitationValidateRequest,
    InvitationValidateResponse,
    JoinOrganizationRequest,
)
from backend.app.schemas.organization_request import (
    OrganizationRequestCreate,
    OrganizationRequestRead,
)
from backend.app.schemas.user import (
    LogoutRequest,
    RoleRead,
    Token,
    TokenRefreshRequest,
    UserCreate,
    UserLogin,
    UserRead,
    UserStatusUpdate,
    UserUpdate,
)
from backend.app.services.auth_service import AuthService
from backend.app.services.invitation_service import InvitationService
from backend.app.services.organization_request_service import OrganizationRequestService

router = APIRouter()


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate user and issue JWT pair",
    dependencies=[Depends(rate_limit_auth)]
)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)) -> Token:
    user = await AuthService.authenticate_user(credentials.email, credentials.password, db)
    return await AuthService.create_user_tokens(user, db)


@router.post("/refresh", response_model=Token, summary="Rotate refresh token and issue new token pair")
async def refresh_token(req: TokenRefreshRequest, db: AsyncSession = Depends(get_db)) -> Token:
    return await AuthService.refresh_access_token(req.refresh_token, db)


@router.post(
    "/join-organization",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register account and join existing organization via valid invitation code",
    dependencies=[Depends(rate_limit_registration)],
)
async def join_organization(
    req: JoinOrganizationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Token:
    client_ip = get_client_ip(request)
    _, token = await InvitationService.redeem_invitation(db, req, client_ip=client_ip)
    return token


@router.post(
    "/invitations/validate",
    response_model=InvitationValidateResponse,
    summary="Validate invitation code status and retrieve associated tenant metadata",
    dependencies=[Depends(rate_limit_auth)],
)
async def validate_invitation(
    req: InvitationValidateRequest,
    db: AsyncSession = Depends(get_db),
) -> InvitationValidateResponse:
    return await InvitationService.validate_invitation(db, req.invitation_code)


@router.post(
    "/organization-requests",
    response_model=OrganizationRequestRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit onboarding request to register a new tenant organization (Pending approval)",
    dependencies=[Depends(rate_limit_registration)],
)
async def create_organization_request(
    req: OrganizationRequestCreate,
    db: AsyncSession = Depends(get_db),
) -> OrganizationRequestRead:
    return await OrganizationRequestService.submit_request(db, req)


@router.post(
    "/invitations",
    response_model=InvitationCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate time-limited invitation for the organization (Company Admin, Super Admin)",
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
    "/invitations",
    response_model=List[InvitationRead],
    summary="List invitations for current organization (Company Admin, Super Admin)",
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


@router.delete(
    "/invitations/{invitation_id}",
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


@router.post("/logout", status_code=status.HTTP_200_OK, summary="Revoke user active refresh tokens")
async def logout(
    data: Optional[LogoutRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    await AuthService.logout_user(
        user=current_user,
        db=db,
        refresh_token_str=data.refresh_token if data else None,
        all_sessions=data.all_sessions if data else False,
    )
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserRead, summary="Retrieve current authenticated user profile")
async def get_me(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserRead:
    ps_res = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    ps = ps_res.scalar_one_or_none()
    is_owner = bool((ps and ps.primary_owner_id == current_user.id) or (ps is None and current_user.is_superuser))
    user_read = UserRead.model_validate(current_user)
    user_read.is_primary_owner = is_owner
    return user_read


@router.get(
    "/roles",
    response_model=List[RoleRead],
    summary="List available roles for user assignment and invitations",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "admin", "it_admin"))]
)
async def list_roles(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[Role]:
    is_super = current_user.is_superuser or any(r.name == "platform_super_admin" for r in current_user.roles)
    q = select(Role).options(selectinload(Role.permissions)).order_by(Role.id)
    roles = list((await db.execute(q)).scalars().all())
    if not is_super:
        roles = [r for r in roles if r.name not in ["platform_super_admin", "company_admin", "admin"]]
    return roles


@router.get(
    "/users",
    response_model=List[UserRead],
    summary="List registered users (Admin, Support, Company Admin)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "admin", "it_admin", "support"))]
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    organization_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
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
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account (Super Admin, Company Admin)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "admin"))]
)
async def create_user(
    user_in: UserCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
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


@router.patch(
    "/users/{user_id}",
    response_model=UserRead,
    summary="Update user details (Super Admin, Company Admin)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "admin"))]
)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await AuthService.update_user(user_id, user_in, current_user, db, scoped_org_id=scoped_org_id)


@router.patch(
    "/users/{user_id}/status",
    response_model=UserRead,
    summary="Update user active/inactive status (Super Admin, Company Admin)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "admin"))]
)
async def update_user_status(
    user_id: int,
    status_in: UserStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await AuthService.update_user_status(user_id, status_in.is_active, current_user, db, scoped_org_id=scoped_org_id)


@router.get(
    "/users/{user_id}",
    response_model=UserRead,
    summary="Get user details by ID (tenant-scoped)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "admin"))]
)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await AuthService.get_user_by_id(user_id, db, scoped_org_id=scoped_org_id)
