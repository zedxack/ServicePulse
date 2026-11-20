"""
ServicePulse - Authentication, Registration & Organization Onboarding Test Suite
Verifies:
- Login authentication & token issuance
- In-memory JWT security architecture
- Invitation creation with role and tenant guardrails
- Atomic invitation validation & redemption
- Concurrency and usage exhaustion protection
- Organization onboarding request & approval workflow
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.rate_limiter import auth_rate_limiter, registration_rate_limiter
from backend.app.models.invitation import OrganizationInvitation
from backend.app.models.user import Role, User


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Clear in-memory rate limiter buckets before each test."""
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
async def test_login_successful_and_returns_tokens(client: AsyncClient):
    """Scenario 1: Authenticate valid user and verify JWT payload structure."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.FIRST_SUPERUSER_EMAIL,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert "platform_super_admin" in data["roles"] or "admin" in data["roles"]


@pytest.mark.asyncio
async def test_login_invalid_credentials_rejected(client: AsyncClient):
    """Scenario 2: Reject invalid password and nonexistent user."""
    resp1 = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.FIRST_SUPERUSER_EMAIL, "password": "WrongPassword2026!"}
    )
    assert resp1.status_code == 401

    resp2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent_user@servicepulse.uz", "password": "AnyPassword2026!"}
    )
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_generate_invitation_success_company_admin(client: AsyncClient, test_db: AsyncSession):
    """Scenario 3: Company Admin generates valid invitation for an employee."""
    admin_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")

    # Find employee role ID
    emp_role = (await test_db.execute(select(Role).where(Role.name == "employee"))).scalar_one()

    resp = await client.post(
        "/api/v1/auth/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "role_id": emp_role.id,
            "max_uses": 2,
            "expires_in_days": 5,
            "invited_email": "new.hire@servicepulse.uz",
        }
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "raw_token" in data
    assert data["raw_token"].startswith("sp_inv_")
    inv = data["invitation"]
    assert inv["role_id"] == emp_role.id
    assert inv["max_uses"] == 2
    assert inv["uses_count"] == 0
    assert inv["is_revoked"] is False
    assert inv["is_valid"] is True


@pytest.mark.asyncio
async def test_generate_invitation_escalation_blocked(client: AsyncClient, test_db: AsyncSession):
    """Scenario 4: Company Admin cannot issue invitations for platform_super_admin role."""
    admin_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")

    # Find platform_super_admin role ID
    super_role = (await test_db.execute(select(Role).where(Role.name == "platform_super_admin"))).scalar_one()

    resp = await client.post(
        "/api/v1/auth/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "role_id": super_role.id,
            "max_uses": 1,
            "expires_in_days": 1,
        }
    )
    assert resp.status_code == 403
    assert "administrative roles" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_validate_invitation_valid_code(client: AsyncClient, test_db: AsyncSession):
    """Scenario 5: Validate a freshly created invitation code."""
    admin_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    emp_role = (await test_db.execute(select(Role).where(Role.name == "employee"))).scalar_one()

    create_resp = await client.post(
        "/api/v1/auth/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "role_id": emp_role.id,
            "max_uses": 1,
            "expires_in_days": 3,
        }
    )
    raw_token = create_resp.json()["raw_token"]

    val_resp = await client.post(
        "/api/v1/auth/invitations/validate",
        json={"invitation_code": raw_token}
    )
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["valid"] is True
    assert val_data["organization_name"] is not None
    assert val_data["role_name"] == "employee"


@pytest.mark.asyncio
async def test_validate_invitation_invalid_or_expired(client: AsyncClient, test_db: AsyncSession):
    """Scenario 6: Validation fails for non-existent and expired invitation codes."""
    # Invalid random code
    resp1 = await client.post(
        "/api/v1/auth/invitations/validate",
        json={"invitation_code": "sp_inv_invalid_fake_code_123456"}
    )
    assert resp1.status_code == 200
    assert resp1.json()["valid"] is False

    # Expired code in database
    admin_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    emp_role = (await test_db.execute(select(Role).where(Role.name == "employee"))).scalar_one()

    create_resp = await client.post(
        "/api/v1/auth/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role_id": emp_role.id, "max_uses": 1, "expires_in_days": 1}
    )
    raw_token = create_resp.json()["raw_token"]
    inv_id = create_resp.json()["invitation"]["id"]

    # Manually expire the invitation in DB
    inv = await test_db.get(OrganizationInvitation, inv_id)
    inv.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await test_db.commit()

    resp2 = await client.post(
        "/api/v1/auth/invitations/validate",
        json={"invitation_code": raw_token}
    )
    assert resp2.status_code == 200
    assert resp2.json()["valid"] is False
    assert "expired" in resp2.json()["error_message"].lower()


@pytest.mark.asyncio
async def test_join_organization_success(client: AsyncClient, test_db: AsyncSession):
    """Scenario 7: Redeem valid invitation, create user, assign role and auto-login."""
    admin_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    support_role = (await test_db.execute(select(Role).where(Role.name == "support"))).scalar_one()

    create_resp = await client.post(
        "/api/v1/auth/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role_id": support_role.id, "max_uses": 1, "expires_in_days": 2}
    )
    raw_token = create_resp.json()["raw_token"]

    join_resp = await client.post(
        "/api/v1/auth/join-organization",
        json={
            "invitation_code": raw_token,
            "full_name": "Alex Morgan",
            "email": "alex.morgan@example.com",
            "password": "SecurePassword2026!",
        }
    )
    assert join_resp.status_code == 201
    token_data = join_resp.json()
    assert "access_token" in token_data
    assert "support" in token_data["roles"]

    # Verify user exists in database with active state
    user_query = select(User).where(User.email == "alex.morgan@example.com")
    user = (await test_db.execute(user_query)).scalar_one_or_none()
    assert user is not None
    assert user.is_active is True
    assert user.organization_id is not None


@pytest.mark.asyncio
async def test_join_organization_exhausted_uses_blocked(client: AsyncClient, test_db: AsyncSession):
    """Scenario 8: Single-use invitation cannot be redeemed twice."""
    admin_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    emp_role = (await test_db.execute(select(Role).where(Role.name == "employee"))).scalar_one()

    create_resp = await client.post(
        "/api/v1/auth/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role_id": emp_role.id, "max_uses": 1, "expires_in_days": 2}
    )
    raw_token = create_resp.json()["raw_token"]

    # First redemption succeeds
    join_resp1 = await client.post(
        "/api/v1/auth/join-organization",
        json={
            "invitation_code": raw_token,
            "full_name": "User One",
            "email": "user.one@example.com",
            "password": "SecurePassword2026!",
        }
    )
    assert join_resp1.status_code == 201

    # Second redemption with same token fails
    join_resp2 = await client.post(
        "/api/v1/auth/join-organization",
        json={
            "invitation_code": raw_token,
            "full_name": "User Two",
            "email": "user.two@example.com",
            "password": "SecurePassword2026!",
        }
    )
    assert join_resp2.status_code == 400
    assert "maximum allowed uses" in join_resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_join_organization_revoked_invitation_blocked(client: AsyncClient, test_db: AsyncSession):
    """Scenario 9: Revoked invitations cannot be redeemed."""
    admin_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    emp_role = (await test_db.execute(select(Role).where(Role.name == "employee"))).scalar_one()

    create_resp = await client.post(
        "/api/v1/auth/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role_id": emp_role.id, "max_uses": 2, "expires_in_days": 2}
    )
    raw_token = create_resp.json()["raw_token"]
    inv_id = create_resp.json()["invitation"]["id"]

    # Revoke invitation
    revoke_resp = await client.delete(
        f"/api/v1/auth/invitations/{inv_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert revoke_resp.status_code == 200

    # Attempt redemption
    join_resp = await client.post(
        "/api/v1/auth/join-organization",
        json={
            "invitation_code": raw_token,
            "full_name": "Late Joiner",
            "email": "late.joiner@example.com",
            "password": "SecurePassword2026!",
        }
    )
    assert join_resp.status_code == 400
    assert "revoked" in join_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_join_organization_weak_password_rejected(client: AsyncClient, test_db: AsyncSession):
    """Scenario 10: Reject password that does not meet enterprise complexity requirements."""
    admin_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    emp_role = (await test_db.execute(select(Role).where(Role.name == "employee"))).scalar_one()

    create_resp = await client.post(
        "/api/v1/auth/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role_id": emp_role.id, "max_uses": 1, "expires_in_days": 2}
    )
    raw_token = create_resp.json()["raw_token"]

    # Password without digits / special characters
    join_resp = await client.post(
        "/api/v1/auth/join-organization",
        json={
            "invitation_code": raw_token,
            "full_name": "Weak Pwd User",
            "email": "weak.user@example.com",
            "password": "simplepassword",
        }
    )
    assert join_resp.status_code == 400
    assert "password must contain" in join_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_submit_organization_request_pending(client: AsyncClient, test_db: AsyncSession):
    """Scenario 11: Register interest for new organization; request stays pending without instant login."""
    resp = await client.post(
        "/api/v1/auth/organization-requests",
        json={
            "org_name": "Samarkand Tech Hub",
            "org_slug": "samarkand-tech",
            "org_email": "info@samarkandtech.uz",
            "contact_full_name": "Jasur Alimov",
            "contact_email": "jasur@samarkandtech.uz",
            "password": "EnterprisePassword2026!",
        }
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["org_slug"] == "samarkand-tech"

    # Verify user CANNOT log in yet
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "jasur@samarkandtech.uz", "password": "EnterprisePassword2026!"}
    )
    assert login_resp.status_code == 401


@pytest.mark.asyncio
async def test_approve_organization_request_platform_super_admin(client: AsyncClient, test_db: AsyncSession):
    """Scenario 12: Super Admin approves request; organization is created and admin can log in."""
    super_token = await get_token(client, settings.FIRST_SUPERUSER_EMAIL, settings.FIRST_SUPERUSER_PASSWORD)

    # Submit request
    req_resp = await client.post(
        "/api/v1/auth/organization-requests",
        json={
            "org_name": "Bukhara Cloud Systems",
            "org_email": "contact@bukharacloud.uz",
            "contact_full_name": "Nodir Karimov",
            "contact_email": "nodir@bukharacloud.uz",
            "password": "BukharaPassword2026!",
        }
    )
    assert req_resp.status_code == 201
    request_id = req_resp.json()["id"]

    # Approve request
    approve_resp = await client.post(
        f"/api/v1/platform/organization-requests/{request_id}/approve",
        headers={"Authorization": f"Bearer {super_token}"}
    )
    assert approve_resp.status_code == 200
    app_data = approve_resp.json()
    assert app_data["status"] == "approved"
    assert app_data["created_organization_id"] is not None
    assert app_data["created_user_id"] is not None

    # Verify new company admin can log in now
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nodir@bukharacloud.uz", "password": "BukharaPassword2026!"}
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert "access_token" in tokens
    assert "company_admin" in tokens["roles"]


@pytest.mark.asyncio
async def test_reject_organization_request(client: AsyncClient, test_db: AsyncSession):
    """Scenario 13: Super Admin rejects organization onboarding request with reason."""
    super_token = await get_token(client, settings.FIRST_SUPERUSER_EMAIL, settings.FIRST_SUPERUSER_PASSWORD)

    # Submit request
    req_resp = await client.post(
        "/api/v1/auth/organization-requests",
        json={
            "org_name": "Spam Corp Ltd",
            "org_email": "spam@example.com",
            "contact_full_name": "Spam Bot",
            "contact_email": "bot@example.com",
            "password": "SpamPassword2026!",
        }
    )
    assert req_resp.status_code == 201
    request_id = req_resp.json()["id"]

    # Reject request
    reject_resp = await client.post(
        f"/api/v1/platform/organization-requests/{request_id}/reject",
        headers={"Authorization": f"Bearer {super_token}"},
        json={"reason": "Invalid business credentials provided."}
    )
    assert reject_resp.status_code == 200
    rej_data = reject_resp.json()
    assert rej_data["status"] == "rejected"
    assert rej_data["rejection_reason"] == "Invalid business credentials provided."


@pytest.mark.asyncio
async def test_rate_limiting_enforced(client: AsyncClient):
    """Scenario 14: Rate limiter enforces limit and returns HTTP 429 with Retry-After header."""
    auth_rate_limiter.requests_per_minute = 3
    auth_rate_limiter._records.clear()

    # First 3 attempts proceed normally (fail with 401 on bad password)
    for _ in range(3):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "attacker@servicepulse.uz", "password": "WrongPassword!"},
            headers={"X-Real-IP": "203.0.113.195"}
        )
        assert r.status_code == 401

    # 4th attempt is rate-limited
    r_limited = await client.post(
        "/api/v1/auth/login",
        json={"email": "attacker@servicepulse.uz", "password": "WrongPassword!"},
        headers={"X-Real-IP": "203.0.113.195"}
    )
    assert r_limited.status_code == 429
    assert "Retry-After" in r_limited.headers
    assert "Rate limit exceeded" in r_limited.json()["detail"]


@pytest.mark.asyncio
async def test_reverse_proxy_header_spoofing_prevented(client: AsyncClient):
    """Scenario 15: Client cannot evade rate limiting by forging X-Forwarded-For prefixes."""
    from starlette.requests import Request

    from backend.app.core.rate_limiter import get_client_ip

    # Simulating request passing through trusted reverse proxy where client sent forged header
    scope = {
        "type": "http",
        "headers": [
            (b"x-real-ip", b"198.51.100.42"),
            (b"x-forwarded-for", b"1.2.3.4, 198.51.100.42"),
        ],
        "client": ("172.20.0.5", 50000),
    }
    req = Request(scope)
    extracted_ip = get_client_ip(req)
    # Must use trusted X-Real-IP rather than spoofed 1.2.3.4
    assert extracted_ip == "198.51.100.42"


@pytest.mark.asyncio
async def test_employee_cannot_issue_invitations(client: AsyncClient, test_db: AsyncSession):
    """Scenario 16: Employee role is forbidden from generating invitations."""
    emp_token = await get_token(client, settings.FIRST_EMPLOYEE_EMAIL, settings.FIRST_EMPLOYEE_PASSWORD)
    emp_role = (await test_db.execute(select(Role).where(Role.name == "employee"))).scalar_one()

    resp = await client.post(
        "/api/v1/auth/invitations",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={"role_id": emp_role.id, "max_uses": 1, "expires_in_days": 1}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_employee_cannot_approve_organization_request(client: AsyncClient, test_db: AsyncSession):
    """Scenario 17: Employee role is forbidden from approving organization onboarding requests."""
    emp_token = await get_token(client, settings.FIRST_EMPLOYEE_EMAIL, settings.FIRST_EMPLOYEE_PASSWORD)

    resp = await client.post(
        "/api/v1/platform/organization-requests/1/approve",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_email_registration_blocked(client: AsyncClient, test_db: AsyncSession):
    """Scenario 18: Redundant registration with an existing active user email is rejected at DB boundary."""
    admin_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    emp_role = (await test_db.execute(select(Role).where(Role.name == "employee"))).scalar_one()

    # Generate invitation
    create_resp = await client.post(
        "/api/v1/auth/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role_id": emp_role.id, "max_uses": 1, "expires_in_days": 2}
    )
    raw_token = create_resp.json()["raw_token"]

    # Try to redeem using the seed employee email which already exists
    join_resp = await client.post(
        "/api/v1/auth/join-organization",
        json={
            "invitation_code": raw_token,
            "full_name": "Duplicate User",
            "email": settings.FIRST_EMPLOYEE_EMAIL,
            "password": "ValidPassword2026!",
        }
    )
    assert join_resp.status_code == 400
    assert "already exists" in join_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_password_hashes_never_returned_in_api(client: AsyncClient, test_db: AsyncSession):
    """Scenario 19: Verify zero password hashes or cryptographic token secrets appear in JSON payloads."""
    super_token = await get_token(client, settings.FIRST_SUPERUSER_EMAIL, settings.FIRST_SUPERUSER_PASSWORD)
    super_h = {"Authorization": f"Bearer {super_token}"}

    # Check /auth/me
    me_resp = await client.get("/api/v1/auth/me", headers=super_h)
    assert me_resp.status_code == 200
    assert "password" not in me_resp.json()
    assert "hashed_password" not in me_resp.json()

    # Check /auth/users
    users_resp = await client.get("/api/v1/auth/users", headers=super_h)
    assert users_resp.status_code == 200
    for u in users_resp.json():
        assert "password" not in u
        assert "hashed_password" not in u

    # Check /platform/organization-requests
    reqs_resp = await client.get("/api/v1/platform/organization-requests", headers=super_h)
    assert reqs_resp.status_code == 200
    for req in reqs_resp.json():
        assert "password" not in req
        assert "hashed_password" not in req
