"""
ServicePulse - Centralized Access Governance Service
Handles authoritative approval/rejection workflows for:
- Organization Registration
- Organization Membership
- Privileged Roles (Company Admin, IT Admin, Support, Executive, Employee)
Only the designated Primary Platform Owner can approve or reject.
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.access_request import AccessRequest
from backend.app.models.audit import AuditLog
from backend.app.models.organization import Organization
from backend.app.models.user import Role, User
from backend.app.schemas.access_request import AccessRequestCreate, AccessRequestStats
from backend.app.services.email_service import email_notification_service
from backend.app.services.organization_request_service import OrganizationRequestService


class AccessRequestService:
    @staticmethod
    async def submit_access_request(
        db: AsyncSession,
        data: AccessRequestCreate,
        requester: Optional[User] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AccessRequest:
        """
        Submit a new access request (membership or role elevation).
        Company Admins can submit requests for their tenant.
        """
        applicant_email = data.applicant_email.strip().lower()

        # Resolve effective organization ID (defaults to requester's organization if omitted)
        effective_org_id = data.organization_id
        if effective_org_id is None and requester and requester.organization_id:
            effective_org_id = requester.organization_id

        # Validate organization if specified
        org = None
        if effective_org_id:
            org = await db.get(Organization, effective_org_id)
            if not org or not org.is_active:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Specified target organization does not exist or is inactive."
                )

            # If requester is a company admin, ensure they belong to this org
            if requester and not requester.is_superuser:
                role_names = {r.name for r in requester.roles}
                if "company_admin" in role_names and requester.organization_id != effective_org_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Company Admins can only submit access requests for their own organization."
                    )

        # Check for existing pending request with same email and type
        pending_q = select(AccessRequest).where(
            AccessRequest.applicant_email == applicant_email,
            AccessRequest.request_type == data.request_type,
            AccessRequest.status == "pending"
        )
        if effective_org_id:
            pending_q = pending_q.where(AccessRequest.organization_id == effective_org_id)

        existing_pending = (await db.execute(pending_q)).scalar_one_or_none()
        if existing_pending:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An access request of type '{data.request_type}' is already pending for this applicant."
            )

        req = AccessRequest(
            request_type=data.request_type,
            status="pending",
            applicant_email=applicant_email,
            applicant_full_name=data.applicant_full_name.strip(),
            organization_id=effective_org_id,
            requester_user_id=requester.id if requester else None,
            target_role_name=data.target_role_name.strip() if data.target_role_name else None,
            justification=data.justification.strip() if data.justification else None,
            client_ip=client_ip,
            user_agent=user_agent[:255] if user_agent else None,
        )
        db.add(req)
        await db.flush()

        # Audit Log
        audit = AuditLog(
            user_id=requester.id if requester else None,
            organization_id=effective_org_id,
            action="access_request_submitted",
            target_resource="access_request",
            target_id=str(req.id),
            status="success",
            details=f"Access request #{req.id} submitted for {applicant_email} (type: {data.request_type})",
        )
        db.add(audit)
        await db.commit()
        await db.refresh(req)

        return req

    @staticmethod
    async def list_requests(
        db: AsyncSession,
        current_user: User,
        status_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AccessRequest]:
        """
        List access requests. Platform admins see all; Company Admins see their org's requests.
        """
        query = (
            select(AccessRequest)
            .options(
                selectinload(AccessRequest.organization),
                selectinload(AccessRequest.requester),
                selectinload(AccessRequest.reviewer),
            )
            .order_by(AccessRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        # Scoping
        is_platform_admin = current_user.is_superuser or any(r.name == "platform_super_admin" for r in current_user.roles)
        if not is_platform_admin:
            if not current_user.organization_id:
                return []
            query = query.where(AccessRequest.organization_id == current_user.organization_id)

        if status_filter:
            query = query.where(AccessRequest.status == status_filter)
        if type_filter:
            query = query.where(AccessRequest.request_type == type_filter)

        res = await db.execute(query)
        return list(res.scalars().all())

    @staticmethod
    async def get_request(
        db: AsyncSession,
        request_id: int,
        current_user: User,
    ) -> AccessRequest:
        """Fetch access request by ID with tenant security check."""
        query = (
            select(AccessRequest)
            .options(
                selectinload(AccessRequest.organization),
                selectinload(AccessRequest.requester),
                selectinload(AccessRequest.reviewer),
            )
            .where(AccessRequest.id == request_id)
        )
        res = await db.execute(query)
        req = res.scalar_one_or_none()
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found.")

        is_platform_admin = current_user.is_superuser or any(r.name == "platform_super_admin" for r in current_user.roles)
        if not is_platform_admin:
            if not current_user.organization_id or req.organization_id != current_user.organization_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        return req

    @staticmethod
    async def approve_request(
        db: AsyncSession,
        request_id: int,
        reviewer: User,
    ) -> AccessRequest:
        """
        Approve access request. Authoritative operation: ONLY Primary Platform Owner.
        """
        req = await db.get(AccessRequest, request_id)
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found.")

        if req.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve request with status '{req.status}'. Only pending requests can be approved."
            )

        # If linked to an organization_request, execute organization provisioning
        if req.organization_request_id:
            await OrganizationRequestService.approve_request(db, req.organization_request_id, reviewer)
        elif req.request_type == "organization_registration":
            # Direct org registration via AccessRequest
            pass
        elif req.target_role_name and req.organization_id:
            # Grant role or activate user in organization
            user_q = select(User).where(User.email == req.applicant_email)
            target_user = (await db.execute(user_q)).scalar_one_or_none()
            role_q = select(Role).where(Role.name == req.target_role_name)
            target_role = (await db.execute(role_q)).scalar_one_or_none()

            if target_user and target_role:
                target_user.organization_id = req.organization_id
                target_user.is_active = True
                if target_role not in target_user.roles:
                    target_user.roles.append(target_role)
                db.add(target_user)

        req.status = "approved"
        req.reviewed_by_id = reviewer.id
        req.reviewed_at = datetime.now(timezone.utc)
        db.add(req)

        # Audit Log
        audit = AuditLog(
            user_id=reviewer.id,
            organization_id=req.organization_id,
            action="access_request_approved",
            target_resource="access_request",
            target_id=str(req.id),
            status="success",
            details=f"Primary Platform Owner approved access request #{req.id} ({req.request_type}) for {req.applicant_email}",
        )
        db.add(audit)
        await db.commit()
        await db.refresh(req)

        # Send approval notification email
        await email_notification_service.send_org_request_approved(req.applicant_email, req.applicant_full_name)

        return req

    @staticmethod
    async def reject_request(
        db: AsyncSession,
        request_id: int,
        reviewer: User,
        reason: str,
    ) -> AccessRequest:
        """
        Reject access request. Authoritative operation: ONLY Primary Platform Owner.
        Requires mandatory non-empty rejection reason.
        """
        if not reason or len(reason.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A non-empty rejection reason (at least 3 characters) is required."
            )

        clean_reason = reason.strip()

        req = await db.get(AccessRequest, request_id)
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found.")

        if req.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject request with status '{req.status}'. Only pending requests can be rejected."
            )

        # If linked to organization_request, reject it too
        if req.organization_request_id:
            await OrganizationRequestService.reject_request(db, req.organization_request_id, reviewer, reason=clean_reason)

        req.status = "rejected"
        req.rejection_reason = clean_reason
        req.reviewed_by_id = reviewer.id
        req.reviewed_at = datetime.now(timezone.utc)
        db.add(req)

        # Audit Log
        audit = AuditLog(
            user_id=reviewer.id,
            organization_id=req.organization_id,
            action="access_request_rejected",
            target_resource="access_request",
            target_id=str(req.id),
            status="success",
            details=f"Primary Platform Owner rejected access request #{req.id} ({req.request_type}) for {req.applicant_email}. Reason: {clean_reason}",
        )
        db.add(audit)
        await db.commit()
        await db.refresh(req)

        # Send rejection notification email
        await email_notification_service.send_org_request_rejected(req.applicant_email, req.applicant_full_name, clean_reason)

        return req

    @staticmethod
    async def get_stats(db: AsyncSession, current_user: User) -> AccessRequestStats:
        """Get summary statistics for access requests."""
        query = select(AccessRequest.status, func.count(AccessRequest.id)).group_by(AccessRequest.status)

        is_platform_admin = current_user.is_superuser or any(r.name == "platform_super_admin" for r in current_user.roles)
        if not is_platform_admin:
            if not current_user.organization_id:
                return AccessRequestStats(pending_count=0, approved_count=0, rejected_count=0, total_count=0)
            query = query.where(AccessRequest.organization_id == current_user.organization_id)

        rows = (await db.execute(query)).all()
        counts = {status: count for status, count in rows}

        pending = counts.get("pending", 0)
        approved = counts.get("approved", 0)
        rejected = counts.get("rejected", 0)
        total = sum(counts.values())

        return AccessRequestStats(
            pending_count=pending,
            approved_count=approved,
            rejected_count=rejected,
            total_count=total,
        )
