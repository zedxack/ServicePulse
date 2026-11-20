"""
ServicePulse - Primary Platform Owner Bootstrap CLI
Provides interactive and non-interactive initialization of the designated Primary Platform Owner.

Usage:
    Interactive:
        python -m backend.app.cli.bootstrap_owner

    Non-Interactive / Scripted:
        python -m backend.app.cli.bootstrap_owner --email owner@example.com --full-name "Primary Owner" --password "SecurePass2026!" [--force]
"""
import argparse
import asyncio
import getpass
import re
import sys
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.security import hash_password, validate_password_strength
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.audit import AuditLog
from backend.app.models.platform_settings import PlatformSettings
from backend.app.models.user import Permission, Role, User

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email_format(email: str) -> bool:
    """Validate RFC 5322 compatible email address format."""
    return bool(EMAIL_REGEX.match(email.strip()))


async def ensure_platform_super_admin_role(db: AsyncSession) -> Role:
    """Ensure platform_super_admin role exists with all permissions."""
    role_q = select(Role).options(selectinload(Role.permissions)).where(Role.name == "platform_super_admin")
    role = (await db.execute(role_q)).scalar_one_or_none()

    perms_res = await db.execute(select(Permission))
    all_perms = list(perms_res.scalars().all())

    if not role:
        role = Role(
            name="platform_super_admin",
            description="Authoritative Platform Super Administrator with full platform control",
            permissions=all_perms,
        )
        db.add(role)
        await db.flush()
    else:
        role.permissions = all_perms
        db.add(role)
        await db.flush()

    return role


async def bootstrap_primary_owner(
    email: str,
    full_name: str,
    password: str,
    force: bool = False,
    db_session: Optional[AsyncSession] = None,
) -> Tuple[bool, str, Optional[User]]:
    """
    Core bootstrap execution logic.
    Idempotent and safe: creates or promotes user and assigns primary owner reference.
    """
    clean_email = email.strip().lower()
    clean_name = full_name.strip()

    if not validate_email_format(clean_email):
        return False, f"Invalid email format: '{clean_email}'", None

    if not clean_name:
        return False, "Full name cannot be empty.", None

    is_strong, pwd_err = validate_password_strength(password)
    if not is_strong:
        return False, f"Password does not meet complexity requirements: {pwd_err}", None

    owns_session = False
    if db_session is None:
        db = AsyncSessionLocal()
        owns_session = True
    else:
        db = db_session

    try:
        # 1. Ensure platform_super_admin role
        super_admin_role = await ensure_platform_super_admin_role(db)

        # 2. Check PlatformSettings singleton
        ps_q = select(PlatformSettings).where(PlatformSettings.id == 1)
        ps = (await db.execute(ps_q)).scalar_one_or_none()

        # 3. Check if user with clean_email exists
        user_q = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.email == clean_email)
        )
        user = (await db.execute(user_q)).scalar_one_or_none()

        # Check existing owner conflict
        if ps and ps.primary_owner_id is not None:
            if user and ps.primary_owner_id == user.id:
                # Same user, re-confirming ownership / updating credentials
                pass
            elif not force:
                return (
                    False,
                    f"A Primary Platform Owner is already designated (User ID: {ps.primary_owner_id}). "
                    "Use --force to transfer platform ownership.",
                    None,
                )

        # 4. Create or promote user
        hashed_pw = hash_password(password)
        now_utc = datetime.now(timezone.utc)

        if not user:
            user = User(
                email=clean_email,
                full_name=clean_name,
                hashed_password=hashed_pw,
                is_active=True,
                is_superuser=True,
                roles=[super_admin_role],
            )
            db.add(user)
            await db.flush()
            created = True
        else:
            user.full_name = clean_name
            user.hashed_password = hashed_pw
            user.is_active = True
            user.is_superuser = True
            if super_admin_role not in user.roles:
                user.roles.append(super_admin_role)
            db.add(user)
            await db.flush()
            created = False

        # 5. Establish PlatformSettings singleton
        if not ps:
            ps = PlatformSettings(
                id=1,
                platform_name="ServicePulse",
                primary_owner_id=user.id,
                allow_public_registration=True,
                bootstrap_completed_at=now_utc,
            )
            db.add(ps)
        else:
            ps.primary_owner_id = user.id
            ps.bootstrap_completed_at = now_utc
            db.add(ps)

        # 6. Audit Log
        audit = AuditLog(
            user_id=user.id,
            action="platform_owner_bootstrapped",
            target_resource="platform_settings",
            target_id=str(user.id),
            status="success",
            details=f"Primary Platform Owner initialized: {user.email} (ID: {user.id}, created: {created})",
        )
        db.add(audit)
        await db.commit()
        await db.refresh(user)

        action_word = "created and designated" if created else "promoted and designated"
        msg = f"Primary Platform Owner successfully {action_word}: {user.email} (User ID: {user.id})"
        return True, msg, user

    except Exception as exc:
        await db.rollback()
        return False, f"Database error during bootstrap: {str(exc)}", None
    finally:
        if owns_session:
            await db.close()


def print_banner() -> None:
    banner = """
========================================================================
       SERVICEPULSE ENTERPRISE — PLATFORM OWNER BOOTSTRAP UTILITY
========================================================================
This tool initializes the designated Primary Platform Owner for
authoritative access governance, organization approvals, and security control.
"""
    print(banner)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap the Primary Platform Owner account for ServicePulse."
    )
    parser.add_argument("--email", "-e", type=str, help="Primary owner corporate email address")
    parser.add_argument("--full-name", "-n", type=str, help="Full name / display name of owner")
    parser.add_argument("--password", "-p", type=str, help="Secure password meeting complexity criteria")
    parser.add_argument("--force", "-f", action="store_true", help="Force ownership transfer if owner exists")

    args = parser.parse_args()

    print_banner()

    email = args.email
    full_name = args.full_name
    password = args.password
    force = args.force

    # Interactive input if flags not fully provided
    if not email:
        while True:
            try:
                email = input("Enter Primary Owner Email Address: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nBootstrap cancelled.")
                sys.exit(1)
            if validate_email_format(email):
                break
            print("  [!] Invalid email format. Please provide a valid address (e.g. owner@example.com).")

    if not full_name:
        while True:
            try:
                full_name = input("Enter Owner Full Name: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nBootstrap cancelled.")
                sys.exit(1)
            if full_name:
                break
            print("  [!] Full name cannot be empty.")

    if not password:
        while True:
            try:
                password = getpass.getpass("Enter Secure Master Password: ")
                confirm = getpass.getpass("Confirm Master Password: ")
            except (KeyboardInterrupt, EOFError):
                print("\nBootstrap cancelled.")
                sys.exit(1)

            if password != confirm:
                print("  [!] Passwords do not match. Please try again.\n")
                continue

            is_strong, err_msg = validate_password_strength(password)
            if not is_strong:
                print(f"  [!] Weak password: {err_msg}\n")
                continue

            break

    print("\nConnecting to database and initializing Primary Platform Owner...")
    success, msg, user = await bootstrap_primary_owner(
        email=email,
        full_name=full_name,
        password=password,
        force=force,
    )

    if success:
        print("\n" + "=" * 72)
        print(" [SUCCESS] PRIMARY PLATFORM OWNER INITIALIZATION COMPLETE")
        print("=" * 72)
        print(f"  Email:              {user.email}")
        print(f"  Full Name:          {user.full_name}")
        print(f"  User ID:            {user.id}")
        print("  Role:               platform_super_admin")
        print("  Superuser Status:   Active (True)")
        print("  Governance Role:    Primary Platform Owner (Sole Authority)")
        print("=" * 72)
        print("You can now sign in at the ServicePulse web console.\n")
        sys.exit(0)
    else:
        print("\n" + "=" * 72)
        print(f" [FAILED] {msg}")
        print("=" * 72)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
