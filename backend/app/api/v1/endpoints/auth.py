"""
ServicePulse - Authentication & User Management Endpoints
Author: Muhammadyusuf Usmonov
"""
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import (
    get_current_active_user,
    get_user_tenant_org_id,
    require_roles,
)
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.user import (
    Token,
    TokenRefreshRequest,
    UserCreate,
    UserLogin,
    UserRead,
    UserStatusUpdate,
    UserUpdate,
)
from backend.app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=Token, summary="Authenticate user and issue JWT pair")
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)) -> Token:
    user = await AuthService.authenticate_user(credentials.email, credentials.password, db)
    return await AuthService.create_user_tokens(user, db)


@router.post("/refresh", response_model=Token, summary="Rotate refresh token and issue new token pair")
async def refresh_token(req: TokenRefreshRequest, db: AsyncSession = Depends(get_db)) -> Token:
    return await AuthService.refresh_access_token(req.refresh_token, db)


@router.post("/logout", status_code=status.HTTP_200_OK, summary="Revoke user active refresh tokens")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    await AuthService.logout_user(current_user, db)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserRead, summary="Retrieve current authenticated user profile")
async def get_me(current_user: User = Depends(get_current_active_user)) -> User:
    return current_user


@router.get(
    "/users",
    response_model=List[UserRead],
    summary="List registered users (Admin, Support, Company Admin)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "admin", "it_admin", "support"))]
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[User]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await AuthService.list_users(skip, limit, db, scoped_org_id=scoped_org_id)


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
) -> User:
    return await AuthService.create_user(user_in, current_user, db)


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
