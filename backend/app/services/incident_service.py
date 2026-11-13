"""
ServicePulse - Incident Management & Concurrency-Safe Deduplication Service
Multi-tenant isolation enforced.
Author: Muhammadyusuf Usmonov
"""
import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.audit import AuditLog
from backend.app.models.incident import Incident, IncidentEvent
from backend.app.models.inventory import Device
from backend.app.models.user import User
from backend.app.schemas.incident import (
    IncidentAcknowledge,
    IncidentAssign,
    IncidentCreate,
    IncidentResolve,
)


class IncidentService:
    @staticmethod
    def generate_fingerprint(org_id: Optional[int], device_id: Optional[int], title: str) -> str:
        raw = f"{org_id or 0}:{device_id or 0}:{title.strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    async def create_or_deduplicate_incident(
        inc_in: IncidentCreate,
        creator: Optional[User],
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Incident:
        """
        Concurrency-safe creation or deduplication of incidents.
        Uses active_dedup_key which is unique across active incidents.
        """
        # Determine organization_id
        target_org_id = scoped_org_id
        if creator:
            is_platform_admin = creator.is_superuser or any(r.name == "platform_super_admin" for r in creator.roles)
            if is_platform_admin:
                target_org_id = inc_in.organization_id or creator.organization_id
            else:
                target_org_id = creator.organization_id
        elif inc_in.organization_id:
            target_org_id = inc_in.organization_id

        # If a device is provided, verify device exists and synchronize organization_id
        if inc_in.device_id:
            dev_q = select(Device).where(Device.id == inc_in.device_id)
            dev = (await db.execute(dev_q)).scalar_one_or_none()
            if not dev:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referenced device not found")
            if target_org_id is not None and dev.organization_id != target_org_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device belongs to another organization")
            if dev.organization_id:
                target_org_id = dev.organization_id

        fingerprint = inc_in.fingerprint or IncidentService.generate_fingerprint(target_org_id, inc_in.device_id, inc_in.title)
        now = datetime.now(timezone.utc)

        # 1. First, search for existing active incident with this deduplication key
        query = (
            select(Incident)
            .options(selectinload(Incident.events))
            .where(Incident.active_dedup_key == fingerprint)
            .with_for_update()
        )
        existing_incident = (await db.execute(query)).scalar_one_or_none()

        if existing_incident:
            # Deduplicate: increment count, update last_seen, add audit event
            existing_incident.occurrence_count += 1
            existing_incident.last_seen_at = now
            # Escalate severity if new event is more severe
            severity_order = {"info": 1, "warning": 2, "critical": 3}
            if severity_order.get(inc_in.severity, 1) > severity_order.get(existing_incident.severity, 1):
                existing_incident.severity = inc_in.severity

            event = IncidentEvent(
                incident_id=existing_incident.id,
                event_type="deduplicated",
                message=f"Occurrence #{existing_incident.occurrence_count} detected: {inc_in.description}",
                created_by_user_id=creator.id if creator else None,
                created_at=now,
            )
            db.add(existing_incident)
            db.add(event)
            await db.commit()
            return await IncidentService.get_incident_by_id(existing_incident.id, db)

        # 2. Otherwise, attempt creation of a new active incident
        new_incident = Incident(
            organization_id=target_org_id,
            device_id=inc_in.device_id,
            fingerprint=fingerprint,
            active_dedup_key=fingerprint,  # Guaranteed unique for active incidents
            title=inc_in.title.strip(),
            description=inc_in.description.strip(),
            severity=inc_in.severity,
            status="open",
            occurrence_count=1,
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(new_incident)

        try:
            await db.flush()
            # Record initial detection event
            init_event = IncidentEvent(
                incident_id=new_incident.id,
                event_type="detected",
                message=f"Incident opened: {new_incident.title}",
                created_by_user_id=creator.id if creator else None,
                created_at=now,
            )
            db.add(init_event)

            db.add(AuditLog(
                user_id=creator.id if creator else None,
                organization_id=target_org_id,
                action="incident_created",
                target_resource="incident",
                target_id=str(new_incident.id),
                status="success",
                details=f"Incident '{new_incident.title}' opened with severity {new_incident.severity}",
            ))
            await db.commit()
            return await IncidentService.get_incident_by_id(new_incident.id, db)

        except IntegrityError:
            # Concurrency conflict: another transaction created the incident with this active_dedup_key in parallel!
            await db.rollback()
            # Retry deduplication on the concurrent winner
            res = await db.execute(
                select(Incident)
                .options(selectinload(Incident.events))
                .where(Incident.active_dedup_key == fingerprint)
            )
            concurrent_incident = res.scalar_one_or_none()
            if concurrent_incident:
                concurrent_incident.occurrence_count += 1
                concurrent_incident.last_seen_at = now
                event = IncidentEvent(
                    incident_id=concurrent_incident.id,
                    event_type="deduplicated",
                    message=f"Concurrent occurrence #{concurrent_incident.occurrence_count} deduplicated safely",
                    created_by_user_id=creator.id if creator else None,
                    created_at=now,
                )
                db.add(concurrent_incident)
                db.add(event)
                await db.commit()
                return await IncidentService.get_incident_by_id(concurrent_incident.id, db)
            raise

    @staticmethod
    async def get_incident_by_id(inc_id: int, db: AsyncSession, scoped_org_id: Optional[int] = None) -> Incident:
        query = (
            select(Incident)
            .options(
                selectinload(Incident.events),
                selectinload(Incident.device),
                selectinload(Incident.assigned_to)
            )
            .where(Incident.id == inc_id)
        )
        incident = (await db.execute(query)).scalar_one_or_none()
        if not incident:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
        if scoped_org_id is not None and incident.organization_id != scoped_org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
        return incident

    @staticmethod
    async def list_incidents(
        skip: int,
        limit: int,
        severity: Optional[str],
        status_val: Optional[str],
        device_id: Optional[int],
        db: AsyncSession,
        scoped_org_id: Optional[int] = None,
    ) -> Tuple[int, List[Incident]]:
        count_q = select(func.count(Incident.id))
        items_q = (
            select(Incident)
            .options(selectinload(Incident.events), selectinload(Incident.device), selectinload(Incident.assigned_to))
            .order_by(Incident.last_seen_at.desc())
            .offset(skip)
            .limit(limit)
        )

        if scoped_org_id is not None:
            count_q = count_q.where(Incident.organization_id == scoped_org_id)
            items_q = items_q.where(Incident.organization_id == scoped_org_id)
        if severity:
            count_q = count_q.where(Incident.severity == severity.strip().lower())
            items_q = items_q.where(Incident.severity == severity.strip().lower())
        if status_val:
            count_q = count_q.where(Incident.status == status_val.strip().lower())
            items_q = items_q.where(Incident.status == status_val.strip().lower())
        if device_id:
            count_q = count_q.where(Incident.device_id == device_id)
            items_q = items_q.where(Incident.device_id == device_id)

        total = (await db.execute(count_q)).scalar() or 0
        items = list((await db.execute(items_q)).scalars().all())
        return total, items

    @staticmethod
    async def assign_incident(
        inc_id: int,
        assign_in: IncidentAssign,
        actor: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Incident:
        incident = await IncidentService.get_incident_by_id(inc_id, db, scoped_org_id=scoped_org_id)
        # Check target user
        target_user = (await db.execute(select(User).where(User.id == assign_in.assigned_to_user_id))).scalar_one_or_none()
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user not found")
        if incident.organization_id is not None and target_user.organization_id != incident.organization_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned user must belong to the incident organization")

        incident.assigned_to_user_id = target_user.id
        if incident.status == "open":
            incident.status = "in_progress"

        event = IncidentEvent(
            incident_id=incident.id,
            event_type="assigned",
            message=f"Incident assigned to {target_user.full_name} ({target_user.email}) by {actor.full_name}",
            created_by_user_id=actor.id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(incident)
        db.add(event)
        await db.commit()
        return await IncidentService.get_incident_by_id(inc_id, db)

    @staticmethod
    async def acknowledge_incident(
        inc_id: int,
        ack_in: IncidentAcknowledge,
        actor: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Incident:
        incident = await IncidentService.get_incident_by_id(inc_id, db, scoped_org_id=scoped_org_id)
        if incident.status == "resolved":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot acknowledge resolved incident")

        incident.status = "acknowledged"
        event = IncidentEvent(
            incident_id=incident.id,
            event_type="acknowledged",
            message=f"Incident acknowledged by {actor.full_name}. Notes: {ack_in.notes or 'None'}",
            created_by_user_id=actor.id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(incident)
        db.add(event)
        await db.commit()
        return await IncidentService.get_incident_by_id(inc_id, db)

    @staticmethod
    async def resolve_incident(
        inc_id: int,
        res_in: IncidentResolve,
        actor: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Incident:
        incident = await IncidentService.get_incident_by_id(inc_id, db, scoped_org_id=scoped_org_id)
        now = datetime.now(timezone.utc)

        incident.status = "resolved"
        incident.resolved_at = now
        incident.resolution_notes = res_in.resolution_notes.strip()

        # CRITICAL: Clear active deduplication key so subsequent failures generate a new incident
        incident.active_dedup_key = None

        event = IncidentEvent(
            incident_id=incident.id,
            event_type="resolved",
            message=f"Resolved by {actor.full_name}: {incident.resolution_notes}",
            created_by_user_id=actor.id,
            created_at=now,
        )
        db.add(incident)
        db.add(event)

        db.add(AuditLog(
            user_id=actor.id,
            organization_id=incident.organization_id,
            action="incident_resolved",
            target_resource="incident",
            target_id=str(incident.id),
            status="success",
            details=f"Incident {incident.id} marked as resolved. Deduplication key cleared.",
        ))
        await db.commit()
        return await IncidentService.get_incident_by_id(inc_id, db)
