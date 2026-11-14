"""
ServicePulse - Organization Onboarding Request Service
Handles public registration requests for new organizations,
and Platform Super Admin review / approval / provisioning workflows.
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
import re
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import hash_password, validate_password_strength
from backend.app.models.audit import AuditLog
from backend.app.models.organization import Organization
from backend.app.models.organization_request import OrganizationRequest
from backend.app.models.user import Role, User
from backend.app.schemas.organization_request import OrganizationRequestCreate
from backend.app.services.email_service import email_notification_service


def slugify(text: str) -> str:
    """Convert text into a clean URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = text.strip("-")
    return text[:50] or "org"


class OrganizationRequestService:
    @staticmethod
    async def submit_request(
        db: AsyncSession,
        data: OrganizationRequestCreate
    ) -> OrganizationRequest:
        """
        Public endpoint handler to register interest for creating a new organization.
        Stores credentials securely; does not grant active access until approved by platform admin.
        """
        # Validate password strength
        valid_pwd, pwd_error = validate_password_strength(data.password)
        if not valid_pwd:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=pwd_error
            )

        contact_email = data.contact_email.strip().lower()

        # Check if contact email already exists as active user
        user_query = select(User).where(User.email == contact_email)
        user_res = await db.execute(user_query)
        if user_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists. Please log in or use an invitation code."
            )

        # Check if pending request exists for contact email
        pending_query = select(OrganizationRequest).where(
            OrganizationRequest.contact_email == contact_email,
            OrganizationRequest.status == "pending"
        )
        pending_res = await db.execute(pending_query)
        if pending_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An organization registration request is already pending for this email address."
            )

        # Generate / validate slug
        candidate_slug = slugify(data.org_slug or data.org_name)
        slug_check = select(Organization).where(Organization.slug == candidate_slug)
        existing_org = (await db.execute(slug_check)).scalar_one_or_none()
        if existing_org:
            # Append timestamp suffix if slug is taken
            candidate_slug = f"{candidate_slug[:42]}-{int(datetime.now().timestamp()) % 100000}"

        # Hash password with Argon2id
        hashed_pw = hash_password(data.password)

        req = OrganizationRequest(
            org_name=data.org_name.strip(),
            org_slug=candidate_slug,
            org_email=data.org_email.strip().lower(),
            org_domain=data.org_domain.strip().lower() if data.org_domain else None,
            contact_full_name=data.contact_full_name.strip(),
            contact_email=contact_email,
            hashed_password=hashed_pw,
            phone=data.phone.strip() if data.phone else None,
            website=data.website.strip() if data.website else None,
            status="pending",
        )
        db.add(req)
        await db.flush()

        # Audit log
        audit = AuditLog(
            action="organization_request_submitted",
            target_resource="organization_request",
            target_id=str(req.id),
            status="success",
            details=f"New organization onboarding request submitted for '{req.org_name}' (slug: {req.org_slug}) by {contact_email}",
        )
        db.add(audit)
        await db.commit()
        await db.refresh(req)

        # Transactional confirmation email
        await email_notification_service.send_org_request_received(contact_email, req.org_name)

        return req

    @staticmethod
    async def list_requests(
        db: AsyncSession,
        status_filter: Optional[str] = None
    ) -> List[OrganizationRequest]:
        """
        List organization requests for Platform Super Admin review.
        """
        query = select(OrganizationRequest).order_by(OrganizationRequest.created_at.desc())
        if status_filter:
            query = query.where(OrganizationRequest.status == status_filter)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_request(
        db: AsyncSession,
        request_id: int
    ) -> OrganizationRequest:
        """Fetch organization request by ID."""
        req = await db.get(OrganizationRequest, request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization request not found."
            )
        return req

    @staticmethod
    async def approve_request(
        db: AsyncSession,
        request_id: int,
        reviewer: User
    ) -> OrganizationRequest:
        """
        Approve an organization request:
        1. Creates and activates the new Organization.
        2. Creates the initial User assigned the 'company_admin' role.
        3. Marks the request as approved.
        4. Audits the action.
        """
        req = await OrganizationRequestService.get_request(db, request_id)
        if req.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve request with status '{req.status}'. Only pending requests can be approved."
            )

        # Check slug collision
        slug_check = select(Organization).where(Organization.slug == req.org_slug)
        existing_org = (await db.execute(slug_check)).scalar_one_or_none()
        final_slug = req.org_slug
        if existing_org:
            final_slug = f"{req.org_slug[:42]}-{int(datetime.now().timestamp()) % 100000}"

        # 1. Create Organization
        new_org = Organization(
            name=req.org_name,
            slug=final_slug,
            is_active=True,
        )
        db.add(new_org)
        await db.flush()

        # 2. Find company_admin role
        role_query = select(Role).where(Role.name == "company_admin")
        role_res = await db.execute(role_query)
        company_admin_role = role_res.scalar_one_or_none()
        if not company_admin_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="System error: 'company_admin' role not found in database."
            )

        # 3. Create Administrator User
        new_user = User(
            email=req.contact_email,
            full_name=req.contact_full_name,
            hashed_password=req.hashed_password,
            organization_id=new_org.id,
            is_active=True,
            is_superuser=False,
            roles=[company_admin_role],
        )
        db.add(new_user)
        await db.flush()

        # 4. Update Request record
        req.status = "approved"
        req.reviewed_by_id = reviewer.id
        req.reviewed_at = datetime.now(timezone.utc)
        req.created_organization_id = new_org.id
        req.created_user_id = new_user.id

        # 5. Audit Log
        audit = AuditLog(
            user_id=reviewer.id,
            action="organization_request_approved",
            target_resource="organization_request",
            target_id=str(req.id),
            organization_id=new_org.id,
            status="success",
            details=f"Approved organization '{new_org.name}' (ID: {new_org.id}) and created administrator '{new_user.email}' (ID: {new_user.id})",
        )
        db.add(audit)
        await db.commit()
        await db.refresh(req)

        # Notify applicant
        await email_notification_service.send_org_request_approved(req.contact_email, req.org_name)

        return req

    @staticmethod
    async def reject_request(
        db: AsyncSession,
        request_id: int,
        reviewer: User,
        reason: Optional[str] = None
    ) -> OrganizationRequest:
        """
        Reject an organization onboarding request.
        """
        req = await OrganizationRequestService.get_request(db, request_id)
        if req.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject request with status '{req.status}'. Only pending requests can be rejected."
            )

        req.status = "rejected"
        req.reviewed_by_id = reviewer.id
        req.reviewed_at = datetime.now(timezone.utc)
        req.rejection_reason = reason

        audit = AuditLog(
            user_id=reviewer.id,
            action="organization_request_rejected",
            target_resource="organization_request",
            target_id=str(req.id),
            status="success",
            details=f"Rejected organization request '{req.org_name}'. Reason: {reason or 'Not specified'}",
        )
        db.add(audit)
        await db.commit()
        await db.refresh(req)

        # Notify applicant
        await email_notification_service.send_org_request_rejected(req.contact_email, req.org_name, reason)

        return req
