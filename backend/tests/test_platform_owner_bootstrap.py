"""
ServicePulse - Platform Owner Bootstrap & Centralized Access Governance Test Suite
Verifies:
- Interactive / scripted CLI bootstrap command logic (bootstrap_primary_owner)
- Primary Platform Owner initialization in PlatformSettings singleton
- Idempotency & transfer protection (transfer requires explicit --force)
- Protection of Primary Platform Owner against deactivation (HTTP 403)
- Protection of Primary Platform Owner against role demotion (HTTP 403)
- Access request submission and status tracking
- Authoritative approval strictly restricted to Primary Platform Owner (Company Admin blocked HTTP 403)
- Authoritative rejection strictly restricted to Primary Platform Owner with mandatory reason (>= 3 chars)
- Tenant isolation on access requests
- Access request stats aggregation
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.cli.bootstrap_owner import bootstrap_primary_owner
from backend.app.core.rate_limiter import auth_rate_limiter, registration_rate_limiter
from backend.app.models.access_request import AccessRequest
from backend.app.models.audit import AuditLog
from backend.app.models.organization import Organization
from backend.app.models.platform_settings import PlatformSettings
from backend.app.models.user import User


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Clear rate limiters before each test run."""
    auth_rate_limiter._records.clear()
    registration_rate_limiter._records.clear()


async def get_token(client: AsyncClient, email: str, password: str) -> str:
    """Helper to authenticate and retrieve access token."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_cli_bootstrap_scripted_success(test_db: AsyncSession):
    """Scenario 1: Scripted bootstrap creates and designates Primary Platform Owner."""
    success, msg, user = await bootstrap_primary_owner(
        email="new.owner@example.com",
        full_name="New Platform Owner",
        password="SecureOwnerPassword2026!",
        force=True,
        db_session=test_db,
    )
    assert success is True
    assert user is not None
    assert user.email == "new.owner@example.com"
    assert user.full_name == "New Platform Owner"
    assert user.is_superuser is True
    assert user.is_active is True
    assert "platform_super_admin" in [r.name for r in user.roles]

    # Verify PlatformSettings singleton record
    ps = (await test_db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))).scalar_one_or_none()
    assert ps is not None
    assert ps.primary_owner_id == user.id
    assert ps.bootstrap_completed_at is not None

    # Verify AuditLog entry
    audit = (
        await test_db.execute(
            select(AuditLog).where(
                AuditLog.action == "platform_owner_bootstrapped",
                AuditLog.target_id == str(user.id),
            )
        )
    ).scalar_one_or_none()
    assert audit is not None
    assert audit.status == "success"


@pytest.mark.asyncio
async def test_cli_bootstrap_idempotency_without_force_fails_on_conflict(test_db: AsyncSession):
    """Scenario 2: Re-running bootstrap for a different user without --force is safely blocked."""
    # First bootstrap establishes owner A
    s1, _, owner_a = await bootstrap_primary_owner(
        email="owner.a@example.com",
        full_name="Owner A",
        password="SecurePassword2026!",
        force=True,
        db_session=test_db,
    )
    assert s1 is True
    assert owner_a is not None

    # Second bootstrap for same user updates details successfully
    s_same, msg_same, _ = await bootstrap_primary_owner(
        email="owner.a@example.com",
        full_name="Owner A Updated",
        password="NewSecurePassword2026!",
        force=False,
        db_session=test_db,
    )
    assert s_same is True
    assert "designated" in msg_same

    # Second bootstrap for DIFFERENT user without --force fails
    s2, msg2, _ = await bootstrap_primary_owner(
        email="owner.b@example.com",
        full_name="Owner B",
        password="SecurePassword2026!",
        force=False,
        db_session=test_db,
    )
    assert s2 is False
    assert "already designated" in msg2
    assert "--force" in msg2

    # With --force, ownership transfer succeeds
    s3, msg3, owner_b = await bootstrap_primary_owner(
        email="owner.b@example.com",
        full_name="Owner B",
        password="SecurePassword2026!",
        force=True,
        db_session=test_db,
    )
    assert s3 is True
    assert owner_b is not None

    ps = (await test_db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))).scalar_one()
    assert ps.primary_owner_id == owner_b.id


@pytest.mark.asyncio
async def test_cli_bootstrap_input_validation(test_db: AsyncSession):
    """Scenario 3: Input validation rejects malformed email, empty name, or weak password."""
    # Bad email
    s, msg, _ = await bootstrap_primary_owner("notanemail", "Name", "Pass2026!", db_session=test_db)
    assert s is False
    assert "Invalid email" in msg

    # Empty name
    s, msg, _ = await bootstrap_primary_owner("valid@example.com", "   ", "Pass2026!", db_session=test_db)
    assert s is False
    assert "cannot be empty" in msg

    # Weak password
    s, msg, _ = await bootstrap_primary_owner("valid@example.com", "Valid Name", "weak", db_session=test_db)
    assert s is False
    assert "complexity" in msg.lower()


@pytest.mark.asyncio
async def test_primary_owner_protection_against_deactivation(client: AsyncClient, test_db: AsyncSession):
    """Scenario 4: Designated Primary Platform Owner cannot be deactivated or locked."""
    # Ensure admin@servicepulse.uz is bootstrapped as primary owner
    await bootstrap_primary_owner(
        email="admin@servicepulse.uz",
        full_name="Platform Admin",
        password="AdminPass2026!",
        force=True,
        db_session=test_db,
    )

    admin_token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")

    # Verify is_primary_owner flag in /auth/me
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["is_primary_owner"] is True
    owner_id = me_data["id"]

    # Attempt to deactivate Primary Platform Owner
    deact_resp = await client.patch(
        f"/api/v1/auth/users/{owner_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert deact_resp.status_code == 403
    assert "cannot deactivate" in deact_resp.json()["detail"].lower()

    # Verify user remains active in database
    owner_user = (await test_db.execute(select(User).where(User.id == owner_id))).scalar_one()
    assert owner_user.is_active is True


@pytest.mark.asyncio
async def test_primary_owner_protection_against_demotion(client: AsyncClient, test_db: AsyncSession):
    """Scenario 5: Primary Platform Owner cannot be stripped of platform_super_admin role."""
    await bootstrap_primary_owner(
        email="admin@servicepulse.uz",
        full_name="Platform Admin",
        password="AdminPass2026!",
        force=True,
        db_session=test_db,
    )

    admin_token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    owner_id = me_resp.json()["id"]

    # Attempt to remove platform_super_admin role
    demote_resp = await client.patch(
        f"/api/v1/auth/users/{owner_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role_names": ["employee"]},
    )
    assert demote_resp.status_code == 403
    assert "cannot remove platform super administrator role" in demote_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_access_request_submission_and_stats(client: AsyncClient, test_db: AsyncSession):
    """Scenario 6: Access request submission and stats counters."""
    comp_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")

    # Submit an access request
    create_resp = await client.post(
        "/api/v1/access-requests",
        headers={"Authorization": f"Bearer {comp_token}"},
        json={
            "request_type": "employee_access",
            "applicant_email": "applicant.test@example.com",
            "applicant_full_name": "Test Applicant",
            "justification": "Requires access to staff portal for departmental operations.",
        },
    )
    assert create_resp.status_code == 200
    req_data = create_resp.json()
    assert req_data["status"] == "pending"
    assert req_data["applicant_email"] == "applicant.test@example.com"
    assert req_data["request_type"] == "employee_access"

    # Query stats as company admin
    stats_resp = await client.get(
        "/api/v1/access-requests/stats",
        headers={"Authorization": f"Bearer {comp_token}"},
    )
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["pending_count"] >= 1
    assert stats["total_count"] >= 1


@pytest.mark.asyncio
async def test_access_request_owner_only_approval(client: AsyncClient, test_db: AsyncSession):
    """Scenario 7: Approval is authoritative and strictly restricted to the Primary Platform Owner."""
    await bootstrap_primary_owner(
        email="admin@servicepulse.uz",
        full_name="Platform Admin",
        password="AdminPass2026!",
        force=True,
        db_session=test_db,
    )

    comp_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    admin_token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")

    # Create access request
    create_resp = await client.post(
        "/api/v1/access-requests",
        headers={"Authorization": f"Bearer {comp_token}"},
        json={
            "request_type": "it_admin_access",
            "applicant_email": "sysadmin.candidate@example.com",
            "applicant_full_name": "Candidate Engineer",
            "justification": "Needs IT admin access for server management.",
        },
    )
    assert create_resp.status_code == 200
    req_id = create_resp.json()["id"]

    # Attempt approval by Company Admin (must be forbidden HTTP 403)
    comp_approve = await client.post(
        f"/api/v1/access-requests/{req_id}/approve",
        headers={"Authorization": f"Bearer {comp_token}"},
    )
    assert comp_approve.status_code == 403
    assert "primary platform owner" in comp_approve.json()["detail"].lower()

    # Authoritative approval by Primary Platform Owner (succeeds)
    owner_approve = await client.post(
        f"/api/v1/access-requests/{req_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert owner_approve.status_code == 200
    approved_data = owner_approve.json()
    assert approved_data["status"] == "approved"
    assert approved_data["reviewed_at"] is not None
    assert approved_data["reviewed_by_id"] is not None

    # Verify audit log for approval
    audit = (
        await test_db.execute(
            select(AuditLog).where(
                AuditLog.action == "access_request_approved",
                AuditLog.target_id == str(req_id),
            )
        )
    ).scalar_one_or_none()
    assert audit is not None
    assert audit.status == "success"


@pytest.mark.asyncio
async def test_access_request_owner_only_rejection_requires_valid_reason(client: AsyncClient, test_db: AsyncSession):
    """Scenario 8: Rejection requires a mandatory reason (min 3 chars) and Primary Owner authority."""
    await bootstrap_primary_owner(
        email="admin@servicepulse.uz",
        full_name="Platform Admin",
        password="AdminPass2026!",
        force=True,
        db_session=test_db,
    )

    comp_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    admin_token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")

    # Create request
    create_resp = await client.post(
        "/api/v1/access-requests",
        headers={"Authorization": f"Bearer {comp_token}"},
        json={
            "request_type": "support_access",
            "applicant_email": "support.candidate@example.com",
            "applicant_full_name": "Support Candidate",
            "justification": "Helpdesk access needed.",
        },
    )
    req_id = create_resp.json()["id"]

    # Attempt rejection by Company Admin (blocked 403)
    comp_rej = await client.post(
        f"/api/v1/access-requests/{req_id}/reject",
        headers={"Authorization": f"Bearer {comp_token}"},
        json={"reason": "Not permitted to reject."},
    )
    assert comp_rej.status_code == 403

    # Primary Owner attempts rejection with reason too short (< 3 chars -> 422 Unprocessable Entity)
    owner_short = await client.post(
        f"/api/v1/access-requests/{req_id}/reject",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "no"},
    )
    assert owner_short.status_code == 422

    # Primary Owner rejects with valid reason
    owner_rej = await client.post(
        f"/api/v1/access-requests/{req_id}/reject",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "Security clearance verification failed for requested role."},
    )
    assert owner_rej.status_code == 200
    rej_data = owner_rej.json()
    assert rej_data["status"] == "rejected"
    assert rej_data["rejection_reason"] == "Security clearance verification failed for requested role."
    assert rej_data["reviewed_by_id"] is not None


@pytest.mark.asyncio
async def test_access_request_tenant_isolation(client: AsyncClient, test_db: AsyncSession):
    """Scenario 9: Company Admins only see requests for their own organization; Super Admin sees all."""
    await bootstrap_primary_owner(
        email="admin@servicepulse.uz",
        full_name="Platform Admin",
        password="AdminPass2026!",
        force=True,
        db_session=test_db,
    )

    admin_token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    comp_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")

    # Create Org 2
    org2 = Organization(name="Second Organization", slug="second-org", domain="second.example.com", is_active=True)
    test_db.add(org2)
    await test_db.flush()

    # Create request for Org 1 (demo org)
    req1 = AccessRequest(
        request_type="employee_access",
        status="pending",
        applicant_email="org1.user@example.com",
        applicant_full_name="Org 1 User",
        organization_id=1,
    )
    # Create request for Org 2
    req2 = AccessRequest(
        request_type="employee_access",
        status="pending",
        applicant_email="org2.user@second.example.com",
        applicant_full_name="Org 2 User",
        organization_id=org2.id,
    )
    test_db.add_all([req1, req2])
    await test_db.commit()

    # Company Admin of Org 1 queries access requests
    comp_list = await client.get("/api/v1/access-requests", headers={"Authorization": f"Bearer {comp_token}"})
    assert comp_list.status_code == 200
    comp_reqs = comp_list.json()
    # Should contain req1 but NEVER req2
    emails = [r["applicant_email"] for r in comp_reqs]
    assert "org1.user@example.com" in emails
    assert "org2.user@second.example.com" not in emails

    # Primary Platform Owner queries all access requests
    admin_list = await client.get("/api/v1/access-requests", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_list.status_code == 200
    admin_emails = [r["applicant_email"] for r in admin_list.json()]
    assert "org1.user@example.com" in admin_emails
    assert "org2.user@second.example.com" in admin_emails
