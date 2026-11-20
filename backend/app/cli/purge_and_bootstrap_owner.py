"""
ServicePulse - Purge Legacy Users & Single Primary Platform Owner Bootstrap Script
Author: Muhammadyusuf Usmonov

Executes atomic database purge and single authoritative owner initialization.
"""
import asyncio
import os
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.orm import selectinload

from backend.app.core.logging import logger
from backend.app.core.security import hash_password
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.access_request import AccessRequest
from backend.app.models.agent import AgentCommand
from backend.app.models.audit import AuditLog
from backend.app.models.incident import Incident, IncidentEvent
from backend.app.models.invitation import OrganizationInvitation
from backend.app.models.monitoring import MaintenanceWindow
from backend.app.models.notification import Notification
from backend.app.models.organization import Organization
from backend.app.models.organization_request import OrganizationRequest
from backend.app.models.platform_settings import PlatformSettings
from backend.app.models.remediation import RemediationExecution
from backend.app.models.ticket import SoftwareRequest, Ticket, TicketComment
from backend.app.models.user import RefreshToken, Role, User, user_roles

TARGET_EMAIL = os.getenv("FIRST_SUPERUSER_EMAIL", "muhammadyusufusmonov011@gmail.com")
TARGET_PASSWORD = os.getenv("FIRST_SUPERUSER_PASSWORD")
if not TARGET_PASSWORD:
    raise RuntimeError("FIRST_SUPERUSER_PASSWORD environment variable must be set to run bootstrap purge.")
TARGET_FULL_NAME = "Muhammadyusuf Usmonov"
TARGET_ROLES = ["platform_super_admin", "company_admin", "it_admin"]


async def purge_and_bootstrap() -> None:
    async with AsyncSessionLocal() as db:
        async with db.begin():
            logger.info("Starting safe atomic user purge and primary owner bootstrap...")

            # 1. Temporarily clear platform_settings.primary_owner_id to prevent RESTRICT violation
            ps_res = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
            ps = ps_res.scalar_one_or_none()
            if ps:
                ps.primary_owner_id = None
                db.add(ps)
                await db.flush()
                logger.info("Cleared platform_settings.primary_owner_id")

            # 2. Clear ephemeral user data tables
            await db.execute(delete(RefreshToken))
            await db.execute(delete(AccessRequest))
            await db.execute(delete(OrganizationInvitation))
            await db.execute(delete(user_roles))
            logger.info("Purged RefreshTokens, AccessRequests, OrganizationInvitations, and UserRoles.")

            # 3. Ensure Organization #1 exists
            org1 = (await db.execute(select(Organization).where(Organization.id == 1))).scalar_one_or_none()
            if not org1:
                org1 = (await db.execute(select(Organization).where(Organization.slug == "demo-org"))).scalar_one_or_none()
            org1_id = org1.id if org1 else 1

            # 4. Check if target user already exists or create target user
            existing_target_res = await db.execute(select(User).where(User.email == TARGET_EMAIL))
            owner_user = existing_target_res.scalar_one_or_none()

            hashed_pw = hash_password(TARGET_PASSWORD)
            now_utc = datetime.now(timezone.utc)

            if not owner_user:
                owner_user = User(
                    email=TARGET_EMAIL,
                    hashed_password=hashed_pw,
                    full_name=TARGET_FULL_NAME,
                    is_active=True,
                    is_superuser=True,
                    organization_id=org1_id,
                    created_at=now_utc,
                    updated_at=now_utc,
                )
                db.add(owner_user)
                await db.flush()
                logger.info("Created Primary Owner account: %s (ID: %d)", TARGET_EMAIL, owner_user.id)
            else:
                owner_user.hashed_password = hashed_pw
                owner_user.full_name = TARGET_FULL_NAME
                owner_user.is_active = True
                owner_user.is_superuser = True
                owner_user.organization_id = org1_id
                owner_user.updated_at = now_utc
                db.add(owner_user)
                await db.flush()
                logger.info("Updated Primary Owner account: %s (ID: %d)", TARGET_EMAIL, owner_user.id)

            owner_id = owner_user.id

            # 5. Reassign non-nullable references to owner_id
            await db.execute(
                update(Ticket).values(author_id=owner_id, assigned_to_id=owner_id)
            )
            await db.execute(
                update(TicketComment).values(author_id=owner_id)
            )
            await db.execute(
                update(SoftwareRequest).values(user_id=owner_id, reviewed_by_user_id=owner_id)
            )

            # 6. Nullify or reassign other foreign keys
            await db.execute(update(Incident).values(assigned_to_user_id=None))
            await db.execute(update(IncidentEvent).values(created_by_user_id=None))
            await db.execute(update(RemediationExecution).values(approved_by_user_id=None))
            await db.execute(update(AgentCommand).values(requested_by_user_id=None))
            await db.execute(update(MaintenanceWindow).values(created_by_user_id=None))
            await db.execute(update(Notification).values(user_id=None))
            await db.execute(update(OrganizationRequest).values(created_user_id=None, reviewed_by_id=None))
            await db.execute(update(AuditLog).values(user_id=None))
            logger.info("Reassigned tickets, comments, and software requests; cleared operational FKs.")

            # 7. Delete all users except the authoritative owner
            del_result = await db.execute(delete(User).where(User.id != owner_id))
            logger.info("Deleted %d legacy user accounts.", del_result.rowcount)

            # 8. Assign roles to owner: platform_super_admin, company_admin, it_admin
            roles_res = await db.execute(select(Role).where(Role.name.in_(TARGET_ROLES)))
            roles_to_assign = list(roles_res.scalars().all())

            # Load user roles relation and assign
            user_with_roles = (
                await db.execute(select(User).options(selectinload(User.roles)).where(User.id == owner_id))
            ).scalar_one()
            user_with_roles.roles = roles_to_assign
            db.add(user_with_roles)
            await db.flush()
            logger.info("Assigned roles to Primary Owner: %s", [r.name for r in roles_to_assign])

            # 9. Configure platform_settings singleton pointing to owner_id
            if not ps:
                ps = PlatformSettings(
                    id=1,
                    platform_name="ServicePulse",
                    primary_owner_id=owner_id,
                    allow_public_registration=True,
                    bootstrap_completed_at=now_utc,
                )
                db.add(ps)
            else:
                ps.primary_owner_id = owner_id
                ps.bootstrap_completed_at = now_utc
                db.add(ps)
            await db.flush()
            logger.info("PlatformSettings singleton updated: primary_owner_id=%d", owner_id)

            # 10. Audit log entry
            audit = AuditLog(
                user_id=owner_id,
                action="platform_owner_purged_and_bootstrapped",
                target_resource="users",
                target_id=str(owner_id),
                status="success",
                details=f"Legacy accounts purged; {TARGET_EMAIL} established as sole Primary Platform Owner.",
            )
            db.add(audit)
            logger.info("Audit log entry created.")

        logger.info("Database transaction committed successfully!")


if __name__ == "__main__":
    asyncio.run(purge_and_bootstrap())
