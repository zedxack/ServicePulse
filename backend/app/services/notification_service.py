"""
ServicePulse - Notification Service
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.notification import Notification
from backend.app.models.user import User
from backend.app.schemas.notification import NotificationCreate
from backend.app.services.ws_manager import ws_manager


class NotificationService:
    @staticmethod
    def generate_fingerprint(org_id: int, category: str, identifier: str) -> str:
        """Create consistent deduplication fingerprint."""
        raw = f"{org_id}:{category}:{identifier}".lower()
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]

    @staticmethod
    async def create_notification(
        arg1=None,
        arg2=None,
        *,
        db: Optional[AsyncSession] = None,
        notif_in: Optional[NotificationCreate] = None,
        dedup_window_minutes: int = 15,
    ) -> Notification:
        """
        Creates an in-app notification with concurrency-safe deduplication.
        If an identical unread notification exists within the cooldown window, deduplicates it.
        Broadcasts real-time alert event via WebSocket.
        """
        session = db
        n_in = notif_in
        for a in (arg1, arg2):
            if isinstance(a, NotificationCreate):
                n_in = a
            elif isinstance(a, AsyncSession):
                session = a

        if not session or not n_in:
            raise ValueError("create_notification requires both AsyncSession and NotificationCreate")

        now = datetime.now(timezone.utc)
        cooldown = now - timedelta(minutes=dedup_window_minutes)

        # Check for existing unread notification with same fingerprint within cooldown
        q = select(Notification).where(
            Notification.organization_id == n_in.organization_id,
            Notification.fingerprint == n_in.fingerprint,
            Notification.is_read.is_(False),
            Notification.created_at >= cooldown,
        )
        existing = (await session.execute(q)).scalar_one_or_none()
        if existing:
            existing.created_at = now
            existing.message = n_in.message
            session.add(existing)
            await session.commit()
            await session.refresh(existing)
            return existing

        notif = Notification(
            organization_id=n_in.organization_id,
            user_id=n_in.user_id,
            target_role=n_in.target_role,
            title=n_in.title.strip(),
            message=n_in.message.strip(),
            severity=n_in.severity,
            category=n_in.category,
            fingerprint=n_in.fingerprint,
            data=n_in.data,
            is_read=False,
            is_dismissed=False,
            created_at=now,
        )
        session.add(notif)
        await session.commit()
        await session.refresh(notif)

        # Real-time WebSocket dispatch
        alert_payload = {
            "id": notif.id,
            "title": notif.title,
            "message": notif.message,
            "severity": notif.severity,
            "category": notif.category,
            "created_at": notif.created_at.isoformat(),
            "data": notif.data,
        }
        if notif.user_id:
            await ws_manager.send_to_user(notif.user_id, "alert:created", alert_payload)
        else:
            await ws_manager.broadcast_to_org(notif.organization_id, "alert:created", alert_payload)

        return notif

    @staticmethod
    async def list_notifications(
        current_user: User,
        skip: int,
        limit: int,
        severity: Optional[str],
        category: Optional[str],
        is_read: Optional[bool],
        db: AsyncSession,
        scoped_org_id: Optional[int] = None,
    ) -> Tuple[int, int, List[Notification]]:
        target_org = scoped_org_id or current_user.organization_id
        user_roles = {r.name for r in current_user.roles}
        privileged = {"platform_super_admin", "company_admin", "admin", "it_admin", "support"}

        base_filter = []
        if target_org is not None:
            base_filter.append(Notification.organization_id == target_org)

        if not current_user.is_superuser and not (user_roles & privileged):
            # Employee isolation
            base_filter.append(
                or_(
                    Notification.user_id == current_user.id,
                    Notification.target_role.is_(None),
                    Notification.target_role == "employee",
                )
            )

        # Filters
        if severity:
            base_filter.append(Notification.severity == severity.strip().lower())
        if category:
            base_filter.append(Notification.category == category.strip().lower())
        if is_read is not None:
            base_filter.append(Notification.is_read.is_(is_read))

        # Total count
        count_q = select(func.count(Notification.id)).where(*base_filter)
        total = (await db.execute(count_q)).scalar() or 0

        # Unread count
        unread_q = select(func.count(Notification.id)).where(
            *base_filter, Notification.is_read.is_(False)
        )
        unread_count = (await db.execute(unread_q)).scalar() or 0

        # Paginated items
        items_q = (
            select(Notification)
            .where(*base_filter)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = list((await db.execute(items_q)).scalars().all())

        return total, unread_count, items

    @staticmethod
    async def get_unread_count(
        current_user: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None,
    ) -> int:
        target_org = scoped_org_id or current_user.organization_id
        user_roles = {r.name for r in current_user.roles}
        privileged = {"platform_super_admin", "company_admin", "admin", "it_admin", "support"}

        base_filter = [Notification.is_read.is_(False)]
        if target_org is not None:
            base_filter.append(Notification.organization_id == target_org)

        if not current_user.is_superuser and not (user_roles & privileged):
            base_filter.append(
                or_(
                    Notification.user_id == current_user.id,
                    Notification.target_role.is_(None),
                    Notification.target_role == "employee",
                )
            )

        q = select(func.count(Notification.id)).where(*base_filter)
        return (await db.execute(q)).scalar() or 0

    @staticmethod
    async def mark_as_read(
        alert_id: int,
        current_user: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None,
    ) -> Notification:
        target_org = scoped_org_id or current_user.organization_id
        q = select(Notification).where(Notification.id == alert_id)
        notif = (await db.execute(q)).scalar_one_or_none()
        if not notif:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

        if target_org is not None and notif.organization_id != target_org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)
        db.add(notif)
        await db.commit()
        await db.refresh(notif)
        return notif

    @staticmethod
    async def mark_all_as_read(
        current_user: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None,
    ) -> int:
        target_org = scoped_org_id or current_user.organization_id
        now = datetime.now(timezone.utc)
        base_filter = [Notification.is_read.is_(False)]
        if target_org is not None:
            base_filter.append(Notification.organization_id == target_org)

        user_roles = {r.name for r in current_user.roles}
        privileged = {"platform_super_admin", "company_admin", "admin", "it_admin", "support"}
        if not current_user.is_superuser and not (user_roles & privileged):
            base_filter.append(
                or_(
                    Notification.user_id == current_user.id,
                    Notification.target_role.is_(None),
                    Notification.target_role == "employee",
                )
            )

        stmt = update(Notification).where(*base_filter).values(is_read=True, read_at=now)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount
