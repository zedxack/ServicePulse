"""
ServicePulse - Authentication & Authorization Dependencies
RBAC, permission verification & per-agent token authentication
Author: Muhammadyusuf Usmonov
"""
import hashlib
from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.security import decode_token
from backend.app.db.session import get_db
from backend.app.models.agent import Agent
from backend.app.models.platform_settings import PlatformSettings
from backend.app.models.user import Role, User

http_bearer = HTTPBearer(auto_error=False)


def hash_agent_token(raw_token: str) -> str:
    """Compute SHA-256 hash of agent token for constant-time DB lookup."""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


async def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Validate JWT access token and retrieve active authenticated user."""
    if not auth_header or not auth_header.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = auth_header.credentials
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"}
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type (expected access token)",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject missing",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token subject",
            headers={"WWW-Authenticate": "Bearer"}
        )

    query = (
        select(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.organization)
        )
        .where(User.id == user_id)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )

    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


def require_roles(*allowed_roles: str) -> Callable:
    """Dependency factory that enforces user role membership."""
    async def role_checker(user: User = Depends(get_current_active_user)) -> User:
        if user.is_superuser:
            return user
        user_role_names = {r.name for r in user.roles}
        if not any(role in user_role_names for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of the following roles: {', '.join(allowed_roles)}"
            )
        return user
    return role_checker


def require_permissions(*required_permissions: str) -> Callable:
    """Dependency factory that enforces granular user permissions."""
    async def permission_checker(user: User = Depends(get_current_active_user)) -> User:
        if user.is_superuser:
            return user
        user_perms = set()
        for role in user.roles:
            for perm in role.permissions:
                user_perms.add(perm.code)

        if not all(p in user_perms for p in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires permission(s): {', '.join(required_permissions)}"
            )
        return user
    return permission_checker


async def get_current_agent(
    x_agent_token: Optional[str] = Header(None, alias="X-Agent-Token"),
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: AsyncSession = Depends(get_db)
) -> Agent:
    """
    Authenticate a remote monitoring agent via X-Agent-Token header
    or Authorization: Bearer <agent_token>.
    """
    token = None
    if x_agent_token:
        token = x_agent_token
    elif auth_header and auth_header.credentials:
        token = auth_header.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent authentication credentials missing (provide X-Agent-Token header or Bearer token)"
        )

    token_hash = hash_agent_token(token)
    query = (
        select(Agent)
        .options(selectinload(Agent.device))
        .where(Agent.api_token_hash == token_hash)
    )
    result = await db.execute(query)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent credentials or revoked token"
        )

    if agent.status not in ["active", "pending"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Agent is not in active state (current status: {agent.status})"
        )

    return agent


def is_platform_super_admin(user: User) -> bool:
    """Check if the user has global platform administrator status."""
    if user.is_superuser:
        return True
    role_names = {r.name for r in user.roles}
    if "platform_super_admin" in role_names:
        return True
    perms = {p.code for r in user.roles for p in r.permissions}
    return "platform:manage" in perms


def get_user_tenant_org_id(user: User) -> Optional[int]:
    """
    Return organization_id for tenant-scoped users, or None if the user
    is a Platform Super Admin with cross-organization visibility.
    """
    if is_platform_super_admin(user):
        return None
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not associated with an active organization"
        )
    return user.organization_id


async def require_platform_admin(
    user: User = Depends(get_current_active_user)
) -> User:
    """Dependency enforcing Platform Super Admin privilege."""
    if not is_platform_super_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires Platform Super Administrator privileges"
        )
    return user

def require_tenant_access(target_org_id: Optional[int], user: User) -> None:
    """
    Validate that user has permission to access resources belonging to target_org_id.
    Raises 403 Forbidden on tenant violation.
    """
    if is_platform_super_admin(user):
        return
    if target_org_id is None or user.organization_id != target_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to resources belonging to another organization is denied"
        )


async def get_platform_settings(db: AsyncSession) -> Optional[PlatformSettings]:
    """Retrieve singleton PlatformSettings row (id=1)."""
    result = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    return result.scalar_one_or_none()


async def is_primary_platform_owner(user: User, db: AsyncSession) -> bool:
    """Check if the user is the designated Primary Platform Owner."""
    ps = await get_platform_settings(db)
    if ps and ps.primary_owner_id is not None:
        return user.id == ps.primary_owner_id
    return user.is_superuser


async def require_primary_owner(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency enforcing Primary Platform Owner privilege.
    Only the Primary Platform Owner has authority to approve/reject
    organization registrations, privileged role requests, and governance approvals.
    """
    owner_verified = await is_primary_platform_owner(user, db)
    if not owner_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires Primary Platform Owner authorization."
        )
    return user

