"""
ServicePulse - Organization Invitation Service
Handles token generation, SHA-256 storage, atomic concurrency-safe redemption,
and role/tenant boundary validation.
Author: Muhammadyusuf Usmonov
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.security import hash_password, validate_password_strength
from backend.app.models.audit import AuditLog
from backend.app.models.invitation import OrganizationInvitation
from backend.app.models.organization import Organization
from backend.app.models.user import Role, User
from backend.app.schemas.invitation import (
    InvitationCreate,
    InvitationValidateResponse,
    JoinOrganizationRequest,
)
from backend.app.schemas.user import Token
from backend.app.services.auth_service import AuthService
from backend.app.services.email_service import email_notification_service


class InvitationService:
    @staticmethod
    def generate_token_pair() -> Tuple[str, str, str]:
        """
        Generate a cryptographically secure invitation token, its SHA-256 hash, and safe prefix.
        Returns (raw_token, token_hash, token_prefix).
        """
        raw_secret = secrets.token_urlsafe(24)
        raw_token = f"sp_inv_{raw_secret}"
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        token_prefix = raw_token[:13]
        return raw_token, token_hash, token_prefix

    @staticmethod
    async def create_invitation(
        db: AsyncSession,
        current_user: User,
        data: InvitationCreate
    ) -> Tuple[OrganizationInvitation, str]:
        """
        Create a new time-limited, revocable invitation with role validation.
        """
        user_role_names = [r.name for r in current_user.roles]
        is_super_admin = "platform_super_admin" in user_role_names
        is_company_admin = "company_admin" in user_role_names

        if not (is_super_admin or is_company_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only platform super administrators and company administrators can create invitations."
            )

        # Determine target organization
        if is_super_admin and data.organization_id is not None:
            target_org_id = data.organization_id
        else:
            target_org_id = current_user.organization_id

        if not target_org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization ID is required to create an invitation."
            )

        # Verify organization exists
        org = await db.get(Organization, target_org_id)
        if not org or not org.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target organization not found or inactive."
            )

        # Verify role exists and role assignment constraints
        if data.role_id is not None:
            role = await db.get(Role, data.role_id)
        elif data.role_name:
            role_q = select(Role).where(Role.name == data.role_name.strip())
            role = (await db.execute(role_q)).scalar_one_or_none()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either role_id or role_name is required to create an invitation."
            )

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target role not found."
            )

        # Company admins cannot invite platform_super_admin or company_admin
        if not is_super_admin:
            if role.name in ["platform_super_admin", "company_admin"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Company administrators cannot issue invitations for administrative roles."
                )

        raw_token, token_hash, token_prefix = InvitationService.generate_token_pair()
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)

        invitation = OrganizationInvitation(
            organization_id=target_org_id,
            role_id=role.id,
            token_hash=token_hash,
            token_prefix=token_prefix,
            created_by_id=current_user.id,
            max_uses=data.max_uses,
            uses_count=0,
            expires_at=expires_at,
            is_revoked=False,
            invited_email=data.invited_email.strip().lower() if data.invited_email else None,
        )
        db.add(invitation)

        # Audit log
        audit = AuditLog(
            user_id=current_user.id,
            action="invitation_created",
            target_resource="invitation",
            target_id=token_prefix,
            organization_id=target_org_id,
            status="success",
            details=f"Created invitation {token_prefix} for role {role.name} in organization {org.name} (max uses: {data.max_uses})",
        )
        db.add(audit)
        await db.commit()
        await db.refresh(invitation)

        # Send email if recipient provided
        if data.invited_email:
            inviter_name = current_user.full_name or "Administrator"
            await email_notification_service.send_invitation_email(
                to_email=data.invited_email,
                inviter_name=inviter_name,
                org_name=org.name,
                invite_code=raw_token,
                role_name=role.name,
            )

        return invitation, raw_token

    @staticmethod
    async def validate_invitation(
        db: AsyncSession,
        raw_token: str
    ) -> InvitationValidateResponse:
        """
        Validate invitation code against current database state.
        Checks expiration, usage count, revocation, and returns organization & role details.
        """
        clean_token = raw_token.strip()
        if len(clean_token) < 8:
            return InvitationValidateResponse(
                valid=False,
                error_message="Invalid invitation token format."
            )

        token_hash = hashlib.sha256(clean_token.encode("utf-8")).hexdigest()
        query = (
            select(OrganizationInvitation)
            .options(
                selectinload(OrganizationInvitation.organization),
                selectinload(OrganizationInvitation.role),
            )
            .where(OrganizationInvitation.token_hash == token_hash)
        )
        result = await db.execute(query)
        invitation = result.scalar_one_or_none()

        if not invitation:
            return InvitationValidateResponse(
                valid=False,
                error_message="Invitation not found or code is invalid."
            )

        if invitation.is_revoked:
            return InvitationValidateResponse(
                valid=False,
                error_message="This invitation has been revoked by an administrator."
            )

        now = datetime.now(timezone.utc)
        exp = invitation.expires_at
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp and exp <= now:
            return InvitationValidateResponse(
                valid=False,
                error_message="This invitation has expired."
            )

        if invitation.uses_count >= invitation.max_uses:
            return InvitationValidateResponse(
                valid=False,
                error_message="This invitation has reached its maximum allowed uses."
            )

        if not invitation.organization or not invitation.organization.is_active:
            return InvitationValidateResponse(
                valid=False,
                error_message="The organization associated with this invitation is inactive."
            )

        return InvitationValidateResponse(
            valid=True,
            organization_id=invitation.organization_id,
            organization_name=invitation.organization.name if invitation.organization else None,
            role_id=invitation.role_id,
            role_name=invitation.role.name if invitation.role else None,
            invited_email=invitation.invited_email,
        )

    @staticmethod
    async def redeem_invitation(
        db: AsyncSession,
        data: JoinOrganizationRequest,
        client_ip: str = "unknown"
    ) -> Tuple[User, Token]:
        """
        Atomically redeem an invitation, creating a new user inside the organization with the assigned role.
        Uses with_for_update() row locking to prevent race conditions on max_uses.
        """
        # Validate password strength
        valid_pwd, pwd_error = validate_password_strength(data.password)
        if not valid_pwd:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=pwd_error
            )

        email_clean = data.email.strip().lower()

        # Check existing user
        user_query = select(User).where(User.email == email_clean)
        user_res = await db.execute(user_query)
        if user_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )

        # Atomic token lock and validation
        token_hash = hashlib.sha256(data.invitation_code.strip().encode("utf-8")).hexdigest()
        inv_query = (
            select(OrganizationInvitation)
            .options(
                selectinload(OrganizationInvitation.organization),
                selectinload(OrganizationInvitation.role),
            )
            .where(OrganizationInvitation.token_hash == token_hash)
            .with_for_update()
        )
        inv_result = await db.execute(inv_query)
        invitation = inv_result.scalar_one_or_none()

        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid invitation code."
            )

        if invitation.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation has been revoked by an administrator."
            )

        now = datetime.now(timezone.utc)
        exp = invitation.expires_at
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp and exp <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation has expired."
            )

        if invitation.uses_count >= invitation.max_uses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation has reached its maximum allowed uses."
            )

        # If email-restricted, enforce exact match
        if invitation.invited_email and invitation.invited_email.lower() != email_clean:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This invitation is designated for a different email address."
            )

        # Consume 1 use
        invitation.uses_count += 1

        # Fetch target role
        role = await db.get(Role, invitation.role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Assigned role not found."
            )

        # Create user
        new_user = User(
            email=email_clean,
            full_name=data.full_name.strip(),
            hashed_password=hash_password(data.password),
            organization_id=invitation.organization_id,
            is_active=True,
            is_superuser=False,
            roles=[role],
        )
        db.add(new_user)
        await db.flush()

        # Audit log for user registration
        audit = AuditLog(
            user_id=new_user.id,
            action="user_registered_via_invitation",
            target_resource="user",
            target_id=str(new_user.id),
            organization_id=invitation.organization_id,
            status="success",
            details=f"User {new_user.email} registered using invitation {invitation.token_prefix} with role {role.name}",
        )
        db.add(audit)
        await db.commit()

        # Issue authentication tokens
        # Re-fetch user with full eager loading for token generation
        query = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == new_user.id)
        )
        loaded_res = await db.execute(query)
        full_user = loaded_res.scalar_one()

        tokens = await AuthService.create_user_tokens(full_user, db)
        return full_user, tokens

    @staticmethod
    async def list_invitations(
        db: AsyncSession,
        current_user: User,
        organization_id: Optional[int] = None,
    ) -> List[OrganizationInvitation]:
        """
        List invitations scoped to the user's organization (or all for platform super admins).
        """
        user_role_names = [r.name for r in current_user.roles]
        is_super_admin = "platform_super_admin" in user_role_names or current_user.is_superuser

        query = (
            select(OrganizationInvitation)
            .options(
                selectinload(OrganizationInvitation.organization),
                selectinload(OrganizationInvitation.role),
            )
            .order_by(OrganizationInvitation.created_at.desc())
        )

        if not is_super_admin:
            query = query.where(OrganizationInvitation.organization_id == current_user.organization_id)
        elif organization_id is not None:
            query = query.where(OrganizationInvitation.organization_id == organization_id)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def revoke_invitation(
        db: AsyncSession,
        invitation_id: int,
        current_user: User
    ) -> OrganizationInvitation:
        """
        Revoke an active invitation. Tenant-isolated: company admins can only revoke their org's invitations.
        """
        user_role_names = [r.name for r in current_user.roles]
        is_super_admin = "platform_super_admin" in user_role_names

        invitation = await db.get(OrganizationInvitation, invitation_id)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found."
            )

        if not is_super_admin and invitation.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization's invitations."
            )

        if not invitation.is_revoked:
            invitation.is_revoked = True
            invitation.revoked_at = datetime.now(timezone.utc)
            invitation.revoked_by_id = current_user.id

            audit = AuditLog(
                user_id=current_user.id,
                action="invitation_revoked",
                target_resource="invitation",
                target_id=invitation.token_prefix,
                organization_id=invitation.organization_id,
                status="success",
                details=f"Invitation {invitation.token_prefix} revoked by user {current_user.id}",
            )
            db.add(audit)
            await db.commit()
            await db.refresh(invitation)

        return invitation
