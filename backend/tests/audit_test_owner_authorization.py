"""
ServicePulse - Independent Audit Test for Database-Authoritative Owner Authorization
Verifies Section 3:
1. Primary owner receives approval/rejection access.
2. Another platform super admin receives 403.
3. Company admin receives 403.
4. Employee receives 403.
5. Stale JWT with is_primary_owner=true claim does NOT retain approval authority after DB ownership transfer.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.cli.bootstrap_owner import bootstrap_primary_owner
from backend.app.core.security import create_access_token, hash_password
from backend.app.models.platform_settings import PlatformSettings
from backend.app.models.user import Role, User


async def get_token(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_database_authoritative_owner_authorization(client: AsyncClient, test_db: AsyncSession):
    # 1. Bootstrap Owner 1 as the designated Primary Platform Owner
    s1, _, owner_1 = await bootstrap_primary_owner(
        email="owner1@example.com",
        full_name="Primary Owner One",
        password="SecurePass2026!",
        force=True,
        db_session=test_db,
    )
    assert s1 is True
    _ = await get_token(client, "owner1@example.com", "SecurePass2026!")

    # 2. Create a second user who also has 'platform_super_admin' role and is_superuser=True
    super_admin_role = (await test_db.execute(select(Role).where(Role.name == "platform_super_admin"))).scalar_one()
    owner_2 = User(
        email="superadmin2@example.com",
        full_name="Second Super Admin",
        hashed_password=hash_password("SecurePass2026!"),
        is_active=True,
        is_superuser=True,
        roles=[super_admin_role],
        organization_id=1,
    )
    test_db.add(owner_2)
    await test_db.commit()
    await test_db.refresh(owner_2)
    superadmin2_token = await get_token(client, "superadmin2@example.com", "SecurePass2026!")

    # 3. Create Company Admin and Employee tokens
    comp_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    emp_token = await get_token(client, "employee@servicepulse.uz", "EmployeePass2026!")

    # 4. Submit a sample access request to approve/reject
    create_resp = await client.post(
        "/api/v1/access-requests",
        headers={"Authorization": f"Bearer {comp_token}"},
        json={
            "request_type": "employee_access",
            "applicant_email": "candidate.audit@example.com",
            "applicant_full_name": "Audit Candidate",
            "justification": "Testing authoritative approval gates.",
        },
    )
    assert create_resp.status_code == 200
    req_id = create_resp.json()["id"]

    # --- ASSERTION 1: Employee receives 403 ---
    emp_approve = await client.post(f"/api/v1/access-requests/{req_id}/approve", headers={"Authorization": f"Bearer {emp_token}"})
    assert emp_approve.status_code == 403, f"Expected 403 for employee, got {emp_approve.status_code}"

    # --- ASSERTION 2: Company Admin receives 403 ---
    comp_approve = await client.post(f"/api/v1/access-requests/{req_id}/approve", headers={"Authorization": f"Bearer {comp_token}"})
    assert comp_approve.status_code == 403, f"Expected 403 for company admin, got {comp_approve.status_code}"

    # --- ASSERTION 3: Second Platform Super Admin receives 403 ---
    super2_approve = await client.post(f"/api/v1/access-requests/{req_id}/approve", headers={"Authorization": f"Bearer {superadmin2_token}"})
    assert super2_approve.status_code == 403, f"Expected 403 for non-owner super admin, got {super2_approve.status_code}"
    assert "primary platform owner" in super2_approve.json()["detail"].lower()

    # --- ASSERTION 4: Stale JWT Claim Invalidation Proof ---
    # Generate a handcrafted JWT with is_primary_owner=True claim for owner_1
    stale_jwt = create_access_token(
        subject=str(owner_1.id),
        claims={
            "email": owner_1.email,
            "full_name": owner_1.full_name,
            "is_superuser": True,
            "is_primary_owner": True,  # Claims to be owner
            "roles": ["platform_super_admin"],
            "permissions": [],
        }
    )

    # Now transfer ownership in the database directly to owner_2
    ps = (await test_db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))).scalar_one()
    ps.primary_owner_id = owner_2.id
    test_db.add(ps)
    await test_db.commit()

    # Attempt approval using the stale JWT for owner_1
    stale_attempt = await client.post(f"/api/v1/access-requests/{req_id}/approve", headers={"Authorization": f"Bearer {stale_jwt}"})
    assert stale_attempt.status_code == 403, f"Stale JWT bypassed DB ownership check! Got {stale_attempt.status_code}"
    assert "primary platform owner" in stale_attempt.json()["detail"].lower()

    # --- ASSERTION 5: Newly designated owner in DB (owner_2) now succeeds ---
    owner2_fresh_token = await get_token(client, "superadmin2@example.com", "SecurePass2026!")
    owner2_approve = await client.post(f"/api/v1/access-requests/{req_id}/approve", headers={"Authorization": f"Bearer {owner2_fresh_token}"})
    assert owner2_approve.status_code == 200, f"New owner approval failed: {owner2_approve.text}"
    assert owner2_approve.json()["status"] == "approved"
    assert owner2_approve.json()["reviewed_by_id"] == owner_2.id
