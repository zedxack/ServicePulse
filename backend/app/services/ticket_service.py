"""
ServicePulse - Helpdesk Tickets & Software Approval Service
Role-based ticket visibility, multi-tenant isolation, employee isolation & software installation workflow.
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.agent import AgentCommand
from backend.app.models.audit import AuditLog
from backend.app.models.inventory import Device
from backend.app.models.ticket import SoftwareRequest, Ticket, TicketComment
from backend.app.models.user import User
from backend.app.schemas.ticket import (
    SoftwareRequestCreate,
    SoftwareRequestReview,
    TicketAssign,
    TicketCommentCreate,
    TicketCreate,
    TicketResolve,
    TicketUpdate,
)


class TicketService:
    # -------------------------------------------------------------------------
    # Helpdesk Tickets
    # -------------------------------------------------------------------------
    @staticmethod
    async def create_ticket(
        t_in: TicketCreate,
        author: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Ticket:
        target_org_id = scoped_org_id or author.organization_id
        if t_in.organization_id and (author.is_superuser or any(r.name == "platform_super_admin" for r in author.roles)):
            target_org_id = t_in.organization_id

        # Validate device if provided
        if t_in.device_id:
            dev = (await db.execute(select(Device).where(Device.id == t_in.device_id))).scalar_one_or_none()
            if not dev:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified device not found")
            if target_org_id is not None and dev.organization_id != target_org_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device belongs to another organization")

        ticket = Ticket(
            organization_id=target_org_id,
            title=t_in.title.strip(),
            description=t_in.description.strip(),
            category=t_in.category.strip().lower(),
            priority=t_in.priority.strip().lower(),
            status="open",
            author_id=author.id,
            device_id=t_in.device_id,
        )
        db.add(ticket)
        await db.flush()

        db.add(AuditLog(
            user_id=author.id,
            organization_id=target_org_id,
            action="ticket_created",
            target_resource="ticket",
            target_id=str(ticket.id),
            status="success",
            details=f"Ticket '{ticket.title}' submitted by {author.email}",
        ))
        await db.commit()
        return await TicketService.get_ticket_by_id(ticket.id, author, db, scoped_org_id=scoped_org_id)

    @staticmethod
    async def get_ticket_by_id(
        t_id: int,
        user: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Ticket:
        q = (
            select(Ticket)
            .options(
                selectinload(Ticket.author),
                selectinload(Ticket.assigned_to),
                selectinload(Ticket.device),
                selectinload(Ticket.comments).selectinload(TicketComment.author),
            )
            .where(Ticket.id == t_id)
        )
        ticket = (await db.execute(q)).scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

        # Tenant isolation
        if scoped_org_id is not None and ticket.organization_id != scoped_org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

        # Employee isolation: Employees can only view tickets they authored
        user_roles = {r.name for r in user.roles}
        privileged = {"admin", "support", "platform_super_admin", "company_admin", "it_admin"}
        if not user.is_superuser and not (user_roles & privileged):
            if ticket.author_id != user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this ticket")

        return ticket

    @staticmethod
    async def list_tickets(
        user: User,
        skip: int,
        limit: int,
        status_val: Optional[str],
        priority: Optional[str],
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> List[Ticket]:
        q = (
            select(Ticket)
            .options(
                selectinload(Ticket.author),
                selectinload(Ticket.assigned_to),
                selectinload(Ticket.device),
                selectinload(Ticket.comments).selectinload(TicketComment.author),
            )
            .order_by(Ticket.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        if scoped_org_id is not None:
            q = q.where(Ticket.organization_id == scoped_org_id)

        user_roles = {r.name for r in user.roles}
        privileged = {"admin", "support", "platform_super_admin", "company_admin", "it_admin"}
        if not user.is_superuser and not (user_roles & privileged):
            # Enforce employee isolation
            q = q.where(Ticket.author_id == user.id)

        if status_val:
            q = q.where(Ticket.status == status_val.strip().lower())
        if priority:
            q = q.where(Ticket.priority == priority.strip().lower())

        return list((await db.execute(q)).scalars().all())

    @staticmethod
    async def update_ticket(
        t_id: int,
        t_in: TicketUpdate,
        user: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Ticket:
        ticket = await TicketService.get_ticket_by_id(t_id, user, db, scoped_org_id=scoped_org_id)

        if t_in.title is not None:
            ticket.title = t_in.title.strip()
        if t_in.description is not None:
            ticket.description = t_in.description.strip()
        if t_in.category is not None:
            ticket.category = t_in.category.strip().lower()
        if t_in.priority is not None:
            ticket.priority = t_in.priority.strip().lower()
        if t_in.status is not None:
            ticket.status = t_in.status.strip().lower()

        db.add(ticket)
        await db.commit()
        return await TicketService.get_ticket_by_id(t_id, user, db, scoped_org_id=scoped_org_id)

    @staticmethod
    async def add_comment(
        t_id: int,
        c_in: TicketCommentCreate,
        user: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> TicketComment:
        ticket = await TicketService.get_ticket_by_id(t_id, user, db, scoped_org_id=scoped_org_id)

        comment = TicketComment(
            ticket_id=ticket.id,
            author_id=user.id,
            comment=c_in.comment.strip(),
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return comment

    @staticmethod
    async def assign_ticket(
        t_id: int,
        assign_in: TicketAssign,
        actor: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Ticket:
        ticket = await TicketService.get_ticket_by_id(t_id, actor, db, scoped_org_id=scoped_org_id)
        target_user = (await db.execute(select(User).where(User.id == assign_in.assigned_to_id))).scalar_one_or_none()
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")
        if ticket.organization_id is not None and target_user.organization_id != ticket.organization_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned user must belong to same organization")

        ticket.assigned_to_id = target_user.id
        if ticket.status == "open":
            ticket.status = "in_progress"

        db.add(ticket)
        db.add(AuditLog(
            user_id=actor.id,
            organization_id=ticket.organization_id,
            action="ticket_assigned",
            target_resource="ticket",
            target_id=str(ticket.id),
            status="success",
            details=f"Ticket {ticket.id} assigned to {target_user.email}",
        ))
        await db.commit()
        return await TicketService.get_ticket_by_id(t_id, actor, db, scoped_org_id=scoped_org_id)

    @staticmethod
    async def resolve_ticket(
        t_id: int,
        res_in: TicketResolve,
        actor: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Ticket:
        ticket = await TicketService.get_ticket_by_id(t_id, actor, db, scoped_org_id=scoped_org_id)
        ticket.status = "resolved"

        if res_in.resolution_notes:
            db.add(TicketComment(
                ticket_id=ticket.id,
                author_id=actor.id,
                comment=f"Resolved with note: {res_in.resolution_notes.strip()}",
            ))

        db.add(ticket)
        db.add(AuditLog(
            user_id=actor.id,
            organization_id=ticket.organization_id,
            action="ticket_resolved",
            target_resource="ticket",
            target_id=str(ticket.id),
            status="success",
            details=f"Ticket {ticket.id} resolved by {actor.email}",
        ))
        await db.commit()
        return await TicketService.get_ticket_by_id(t_id, actor, db, scoped_org_id=scoped_org_id)

    # -------------------------------------------------------------------------
    # Software Approval Workflow
    # -------------------------------------------------------------------------
    @staticmethod
    async def create_software_request(
        req_in: SoftwareRequestCreate,
        user: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> SoftwareRequest:
        target_org_id = scoped_org_id or user.organization_id
        dev = (await db.execute(select(Device).where(Device.id == req_in.device_id))).scalar_one_or_none()
        if not dev:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target device not found")
        if target_org_id is not None and dev.organization_id != target_org_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device belongs to another organization")

        req = SoftwareRequest(
            organization_id=target_org_id,
            user_id=user.id,
            device_id=dev.id,
            software_name=req_in.software_name.strip(),
            software_version=req_in.software_version.strip() if req_in.software_version else None,
            reason=req_in.reason.strip(),
            status="pending",
        )
        db.add(req)
        await db.flush()

        db.add(AuditLog(
            user_id=user.id,
            organization_id=target_org_id,
            action="software_request_submitted",
            target_resource="software_request",
            target_id=str(req.id),
            status="success",
            details=f"Request to install {req.software_name} on device {dev.hostname}",
        ))
        await db.commit()
        return await TicketService.get_software_request_by_id(req.id, user, db, scoped_org_id=scoped_org_id)

    @staticmethod
    async def get_software_request_by_id(
        req_id: int,
        user: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> SoftwareRequest:
        q = (
            select(SoftwareRequest)
            .options(selectinload(SoftwareRequest.user), selectinload(SoftwareRequest.device))
            .where(SoftwareRequest.id == req_id)
        )
        req = (await db.execute(q)).scalar_one_or_none()
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Software request not found")

        if scoped_org_id is not None and req.organization_id != scoped_org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Software request not found")

        user_roles = {r.name for r in user.roles}
        privileged = {"admin", "support", "platform_super_admin", "company_admin", "it_admin"}
        if not user.is_superuser and not (user_roles & privileged):
            if req.user_id != user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return req

    @staticmethod
    async def list_software_requests(
        user: User,
        skip: int,
        limit: int,
        status_val: Optional[str],
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> List[SoftwareRequest]:
        q = (
            select(SoftwareRequest)
            .options(selectinload(SoftwareRequest.user), selectinload(SoftwareRequest.device))
            .order_by(SoftwareRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        if scoped_org_id is not None:
            q = q.where(SoftwareRequest.organization_id == scoped_org_id)

        user_roles = {r.name for r in user.roles}
        privileged = {"admin", "support", "platform_super_admin", "company_admin", "it_admin"}
        if not user.is_superuser and not (user_roles & privileged):
            q = q.where(SoftwareRequest.user_id == user.id)

        if status_val:
            q = q.where(SoftwareRequest.status == status_val.strip().lower())

        return list((await db.execute(q)).scalars().all())

    @staticmethod
    async def approve_software_request(
        req_id: int,
        review_in: SoftwareRequestReview,
        reviewer: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> SoftwareRequest:
        req = await TicketService.get_software_request_by_id(req_id, reviewer, db, scoped_org_id=scoped_org_id)
        if req.status != "pending":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request is already {req.status}")

        now = datetime.now(timezone.utc)
        req.status = "approved"
        req.reviewed_by_user_id = reviewer.id
        req.review_notes = review_in.review_notes
        req.reviewed_at = now

        # Create securely validated pending agent command if device has registered agent
        q_dev = select(Device).options(selectinload(Device.agent)).where(Device.id == req.device_id)
        dev = (await db.execute(q_dev)).scalar_one_or_none()
        if dev and dev.agent:
            cmd = AgentCommand(
                agent_id=dev.agent.id,
                device_id=dev.id,
                action_name="install_approved_software",
                parameters=f'{{"software": "{req.software_name}", "version": "{req.software_version or ""}"}}',
                status="pending",
                verification_status="pending",
                requested_by_user_id=reviewer.id,
            )
            db.add(cmd)

        db.add(req)
        db.add(AuditLog(
            user_id=reviewer.id,
            organization_id=req.organization_id,
            action="software_request_approved",
            target_resource="software_request",
            target_id=str(req.id),
            status="success",
            details=f"Approved installation of {req.software_name} for device {req.device_id}",
        ))
        await db.commit()
        return await TicketService.get_software_request_by_id(req_id, reviewer, db, scoped_org_id=scoped_org_id)

    @staticmethod
    async def reject_software_request(
        req_id: int,
        review_in: SoftwareRequestReview,
        reviewer: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> SoftwareRequest:
        req = await TicketService.get_software_request_by_id(req_id, reviewer, db, scoped_org_id=scoped_org_id)
        if req.status != "pending":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request is already {req.status}")

        now = datetime.now(timezone.utc)
        req.status = "rejected"
        req.reviewed_by_user_id = reviewer.id
        req.review_notes = review_in.review_notes
        req.reviewed_at = now

        db.add(req)
        db.add(AuditLog(
            user_id=reviewer.id,
            organization_id=req.organization_id,
            action="software_request_rejected",
            target_resource="software_request",
            target_id=str(req.id),
            status="success",
            details=f"Rejected installation of {req.software_name}. Reason: {review_in.review_notes or 'Not provided'}",
        ))
        await db.commit()
        return await TicketService.get_software_request_by_id(req_id, reviewer, db, scoped_org_id=scoped_org_id)
