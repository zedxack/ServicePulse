"""
ServicePulse - Authentication & User Management Service
Handles password validation, JWT issuance, refresh token rotation, and RBAC.
Author: Muhammadyusuf Usmonov
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from backend.app.models.audit import AuditLog
from backend.app.models.user import RefreshToken, Role, User
from backend.app.schemas.user import Token, UserCreate, UserUpdate


class AuthService:
    @staticmethod
    async def authenticate_user(email: str, password: str, db: AsyncSession) -> User:
        """Authenticate user by email and Argon2id password hash."""
        query = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.email == email.strip().lower())
        )
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            # Log failed authentication attempt
            audit = AuditLog(
                user_id=user.id if user else None,
                action="auth_login_failed",
                target_resource="user",
                target_id=email,
                status="failure",
                details="Invalid email or password",
            )
            db.add(audit)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive. Please contact system administrator."
            )

        # Update last login timestamp
        user.last_login = datetime.now(timezone.utc)
        db.add(user)

        # Log successful login
        audit = AuditLog(
            user_id=user.id,
            action="auth_login_success",
            target_resource="user",
            target_id=str(user.id),
            status="success",
            details="User logged in successfully",
        )
        db.add(audit)
        await db.commit()
        return user

    @staticmethod
    async def create_user_tokens(user: User, db: AsyncSession) -> Token:
        """Issue access token and a database-tracked refresh token with unique jti."""
        jti = uuid.uuid4().hex
        role_names = [r.name for r in user.roles]
        permissions = [p.code for r in user.roles for p in r.permissions]

        claims = {
            "email": user.email,
            "full_name": user.full_name,
            "roles": role_names,
            "permissions": permissions,
            "is_superuser": user.is_superuser,
            "organization_id": user.organization_id,
            "primary_dashboard": user.primary_dashboard,
        }

        access_token = create_access_token(subject=str(user.id), claims=claims)
        refresh_token = create_refresh_token(subject=str(user.id))

        # Store refresh token record for revocation & rotation tracking
        decoded_refresh = decode_token(refresh_token)
        expires_at = (
            datetime.fromtimestamp(decoded_refresh["exp"], tz=timezone.utc)
            if "exp" in decoded_refresh
            else datetime.now(timezone.utc)
        )

        token_record = RefreshToken(
            user_id=user.id,
            token_jti=jti,
            revoked=False,
            expires_at=expires_at,
        )
        db.add(token_record)
        await db.commit()

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            primary_dashboard=user.primary_dashboard,
            organization_id=user.organization_id,
            full_name=user.full_name,
            roles=role_names,
        )

    @staticmethod
    async def refresh_access_token(refresh_token_str: str, db: AsyncSession) -> Token:
        """Validate refresh token, enforce single-use rotation, and issue new pair."""
        try:
            payload = decode_token(refresh_token_str)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid refresh token: {str(exc)}",
            ) from exc

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Provided token is not a refresh token",
            )

        user_id = int(payload["sub"])
        query = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == user_id)
        )
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Check existing active refresh tokens
        query_token = (
            select(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked == False)  # noqa: E712
            .order_by(RefreshToken.created_at.desc())
        )
        res = await db.execute(query_token)
        latest_token = res.scalars().first()

        # Enforce rotation: revoke previous token
        if latest_token:
            latest_token.revoked = True
            db.add(latest_token)

        # Generate new token pair
        new_tokens = await AuthService.create_user_tokens(user, db)
        return new_tokens

    @staticmethod
    async def logout_user(user: User, db: AsyncSession) -> None:
        """Revoke all active refresh tokens for the logging-out user."""
        query = select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked == False)  # noqa: E712
        result = await db.execute(query)
        active_tokens = result.scalars().all()
        for tok in active_tokens:
            tok.revoked = True
            db.add(tok)

        audit = AuditLog(
            user_id=user.id,
            action="auth_logout",
            target_resource="user",
            target_id=str(user.id),
            status="success",
            details="User logged out; active tokens revoked",
        )
        db.add(audit)
        await db.commit()

    @staticmethod
    async def create_user(user_in: UserCreate, creator: Optional[User], db: AsyncSession) -> User:
        """Create a new user with Argon2id hashed password and assigned roles."""
        # Check duplicate email
        query = select(User).where(User.email == user_in.email.strip().lower())
        existing = (await db.execute(query)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email '{user_in.email}' already exists",
            )

        # Multi-tenant isolation: Platform super admin can assign any org; tenant admin can only assign own org
        target_org_id = user_in.organization_id
        if creator is not None:
            is_platform_admin = creator.is_superuser or any(r.name == "platform_super_admin" for r in creator.roles)
            if not is_platform_admin:
                if target_org_id is not None and target_org_id != creator.organization_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot create users outside your assigned organization"
                    )
                target_org_id = creator.organization_id
                if user_in.is_superuser:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot assign superuser privileges"
                    )
                if "platform_super_admin" in user_in.role_names:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot assign platform super administrator role"
                    )

        # Fetch requested roles
        roles_query = select(Role).where(Role.name.in_(user_in.role_names))
        roles_res = await db.execute(roles_query)
        roles = roles_res.scalars().all()

        user = User(
            email=user_in.email.strip().lower(),
            hashed_password=hash_password(user_in.password),
            full_name=user_in.full_name.strip(),
            is_active=user_in.is_active,
            is_superuser=user_in.is_superuser,
            organization_id=target_org_id,
            roles=roles,
        )
        db.add(user)
        await db.flush()

        audit = AuditLog(
            user_id=creator.id if creator else None,
            organization_id=target_org_id,
            action="user_created",
            target_resource="user",
            target_id=str(user.id),
            status="success",
            details=f"Created user {user.email} with roles: {', '.join(user_in.role_names)}",
        )
        db.add(audit)
        await db.commit()

        # Re-fetch with relationships loaded
        return await AuthService.get_user_by_id(user.id, db)

    @staticmethod
    async def get_user_by_id(user_id: int, db: AsyncSession, scoped_org_id: Optional[int] = None) -> User:
        query = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
                selectinload(User.organization)
            )
            .where(User.id == user_id)
        )
        res = await db.execute(query)
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if scoped_org_id is not None and user.organization_id != scoped_org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return user

    @staticmethod
    async def list_users(skip: int, limit: int, db: AsyncSession, scoped_org_id: Optional[int] = None) -> List[User]:
        query = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
                selectinload(User.organization)
            )
            .order_by(User.id)
            .offset(skip)
            .limit(limit)
        )
        if scoped_org_id is not None:
            query = query.where(User.organization_id == scoped_org_id)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_user(
        user_id: int,
        user_in: UserUpdate,
        modifier: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> User:
        user = await AuthService.get_user_by_id(user_id, db, scoped_org_id=scoped_org_id)

        if user_in.email:
            # Check unique
            q = select(User).where(User.email == user_in.email.strip().lower(), User.id != user_id)
            if (await db.execute(q)).scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already taken")
            user.email = user_in.email.strip().lower()

        if user_in.full_name:
            user.full_name = user_in.full_name.strip()

        if user_in.password:
            user.hashed_password = hash_password(user_in.password)

        if user_in.role_names is not None:
            # If modifier is not platform admin, prevent granting platform_super_admin
            is_platform_admin = modifier.is_superuser or any(r.name == "platform_super_admin" for r in modifier.roles)
            if not is_platform_admin and "platform_super_admin" in user_in.role_names:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot assign platform super administrator role"
                )
            roles_query = select(Role).where(Role.name.in_(user_in.role_names))
            roles = (await db.execute(roles_query)).scalars().all()
            user.roles = roles

        if user_in.organization_id is not None:
            is_platform_admin = modifier.is_superuser or any(r.name == "platform_super_admin" for r in modifier.roles)
            if not is_platform_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot reassign organization"
                )
            user.organization_id = user_in.organization_id

        db.add(user)
        audit = AuditLog(
            user_id=modifier.id,
            organization_id=user.organization_id,
            action="user_updated",
            target_resource="user",
            target_id=str(user.id),
            status="success",
            details=f"Updated user {user.id}",
        )
        db.add(audit)
        await db.commit()
        return await AuthService.get_user_by_id(user_id, db)

    @staticmethod
    async def update_user_status(
        user_id: int,
        is_active: bool,
        modifier: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> User:
        user = await AuthService.get_user_by_id(user_id, db, scoped_org_id=scoped_org_id)
        user.is_active = is_active
        db.add(user)

        audit = AuditLog(
            user_id=modifier.id,
            organization_id=user.organization_id,
            action="user_status_changed",
            target_resource="user",
            target_id=str(user.id),
            status="success",
            details=f"User active status changed to {is_active}",
        )
        db.add(audit)
        await db.commit()
        return await AuthService.get_user_by_id(user_id, db)
