"""
ServicePulse - Access Approval Security Audit Test Suite
Verifies Section 4 of Primary Owner Acceptance Audit:
1. Coverage of all 7 request types.
2. Privilege escalation prevention (cannot self-assign or assign invalid roles).
3. Self-approval prevention (requester cannot approve own request).
4. Company admin boundaries (403 on approval, 403 on cross-tenant submissions).
5. Invitation redemption security & single-use enforcement.
6. Concurrency test (duplicate approval / race condition resilience).
7. Rejection validation (reason validation, audit log persistence).
8. Cross-tenant isolation (Org 1 admin cannot view or access Org 2 requests).
"""
import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.cli.bootstrap_owner import bootstrap_primary_owner
from backend.app.core.rate_limiter import (
    auth_rate_limiter,
    invitation_rate_limiter,
    registration_rate_limiter,
)
from backend.app.models.access_request import AccessRequest
from backend.app.models.audit import AuditLog
from backend.app.models.organization import Organization
from backend.app.models.user import Role


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    auth_rate_limiter._records.clear()
    registration_rate_limiter._records.clear()
    invitation_rate_limiter._records.clear()


async def get_token(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_all_seven_request_types_handling(client: AsyncClient, test_db: AsyncSession):
    """Verify all 7 request types are supported, tracked, and governable by the primary owner."""
    await bootstrap_primary_owner(
        email="admin@servicepulse.uz",
        full_name="Platform Owner",
        password="AdminPass2026!",
        force=True,
        db_session=test_db,
    )
    owner_token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")

    types = [
        ("organization_registration", "org_reg@example.com", "Applicant Org"),
        ("organization_membership", "org_mem@example.com", "Applicant Member"),
        ("employee_access", "emp_req@example.com", "Applicant Emp"),
        ("support_access", "sup_req@example.com", "Applicant Sup"),
        ("it_admin_access", "it_req@example.com", "Applicant IT"),
        ("company_admin_access", "comp_req@example.com", "Applicant CompAdmin"),
        ("executive_access", "exec_req@example.com", "Applicant Exec"),
    ]

    for req_type, email, full_name in types:
        create_resp = await client.post(
            "/api/v1/access-requests",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "request_type": req_type,
                "applicant_email": email,
                "applicant_full_name": full_name,
                "organization_id": 1 if req_type != "organization_registration" else None,
                "justification": f"Validating governance for {req_type}",
            },
        )
        assert create_resp.status_code == 200, f"Failed for {req_type}: {create_resp.text}"
        data = create_resp.json()
        assert data["request_type"] == req_type
        assert data["status"] == "pending"
        req_id = data["id"]

        # Primary owner can approve
        approve_resp = await client.post(
            f"/api/v1/access-requests/{req_id}/approve",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert approve_resp.status_code == 200, f"Approval failed for {req_type}: {approve_resp.text}"
        assert approve_resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_privilege_escalation_and_self_approval_prevention(client: AsyncClient, test_db: AsyncSession):
    """Verify company admin or employee cannot approve own or others' requests, nor escalate privileges."""
    await bootstrap_primary_owner(
        email="admin@servicepulse.uz",
        full_name="Platform Owner",
        password="AdminPass2026!",
        force=True,
        db_session=test_db,
    )
    comp_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    emp_token = await get_token(client, "employee@servicepulse.uz", "EmployeePass2026!")

    # 1. Company admin submits request for elevated executive access for themselves
    sub_resp = await client.post(
        "/api/v1/access-requests",
        headers={"Authorization": f"Bearer {comp_token}"},
        json={
            "request_type": "executive_access",
            "applicant_email": "company_admin@servicepulse.uz",
            "applicant_full_name": "Company Admin User",
            "justification": "Elevating to executive role",
        },
    )
    assert sub_resp.status_code == 200
    req_id = sub_resp.json()["id"]

    # 2. Company admin attempts self-approval
    self_appr = await client.post(
        f"/api/v1/access-requests/{req_id}/approve",
        headers={"Authorization": f"Bearer {comp_token}"},
    )
    assert self_appr.status_code == 403, "Company admin self-approved access request!"

    # 3. Employee attempts approval
    emp_appr = await client.post(
        f"/api/v1/access-requests/{req_id}/approve",
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert emp_appr.status_code == 403, "Employee approved access request!"


@pytest.mark.asyncio
async def test_company_admin_boundaries_and_cross_tenant_isolation(client: AsyncClient, test_db: AsyncSession):
    """Verify company admin cannot access or submit requests for other organizations."""
    await bootstrap_primary_owner(
        email="admin@servicepulse.uz",
        full_name="Platform Owner",
        password="AdminPass2026!",
        force=True,
        db_session=test_db,
    )
    comp_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")

    # Create Org 2
    org2 = Organization(name="Target Tenant B", slug="target-tenant-b", domain="tenantb.example.com", is_active=True)
    test_db.add(org2)
    await test_db.flush()

    # Org 1 admin tries to submit request targetting Org 2
    cross_sub = await client.post(
        "/api/v1/access-requests",
        headers={"Authorization": f"Bearer {comp_token}"},
        json={
            "request_type": "employee_access",
            "applicant_email": "candidate@tenantb.example.com",
            "applicant_full_name": "Tenant B Candidate",
            "organization_id": org2.id,
            "justification": "Illegal cross-tenant submission",
        },
    )
    assert cross_sub.status_code == 403, "Company admin successfully submitted request for another tenant!"

    # Seed an existing request under Org 2
    req_org2 = AccessRequest(
        request_type="employee_access",
        status="pending",
        applicant_email="candidate2@tenantb.example.com",
        applicant_full_name="Candidate 2",
        organization_id=org2.id,
    )
    test_db.add(req_org2)
    await test_db.commit()
    await test_db.refresh(req_org2)

    # Org 1 admin attempts to GET Org 2 request detail
    get_res = await client.get(
        f"/api/v1/access-requests/{req_org2.id}",
        headers={"Authorization": f"Bearer {comp_token}"},
    )
    assert get_res.status_code == 403, f"Expected 403 for cross-tenant request inspection, got {get_res.status_code}"


@pytest.mark.asyncio
async def test_invitation_redemption_and_single_use_enforcement(client: AsyncClient, test_db: AsyncSession):
    """Verify invitation creation, single-use token rotation, and invalidation."""
    await bootstrap_primary_owner(
        email="admin@servicepulse.uz",
        full_name="Platform Owner",
        password="AdminPass2026!",
        force=True,
        db_session=test_db,
    )
    comp_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")

    # 1. Create a single-use invitation (max_uses=1)
    emp_role = (await test_db.execute(select(Role).where(Role.name == "employee"))).scalar_one()
    inv_resp = await client.post(
        "/api/v1/auth/invitations",
        headers={"Authorization": f"Bearer {comp_token}"},
        json={
            "role_id": emp_role.id,
            "max_uses": 1,
            "expires_in_days": 1,
            "invited_email": "onetime.user@example.com",
        },
    )
    assert inv_resp.status_code == 201
    raw_code = inv_resp.json()["raw_token"]

    # 2. First redemption succeeds
    join_resp1 = await client.post(
        "/api/v1/auth/join-organization",
        json={
            "invitation_code": raw_code,
            "email": "onetime.user@example.com",
            "full_name": "One Time User",
            "password": "SecurePassword2026!",
        },
    )
    assert join_resp1.status_code == 201
    assert "access_token" in join_resp1.json()

    # 3. Second redemption with the exact same code MUST fail (HTTP 400 - max uses reached)
    join_resp2 = await client.post(
        "/api/v1/auth/join-organization",
        json={
            "invitation_code": raw_code,
            "email": "second.user@example.com",
            "full_name": "Second User",
            "password": "SecurePassword2026!",
        },
    )
    assert join_resp2.status_code == 400
    assert "maximum allowed uses" in join_resp2.json()["detail"].lower() or "no longer valid" in join_resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_rejection_validation_and_audit_log_persistence(client: AsyncClient, test_db: AsyncSession):
    """Verify rejection enforces reason rules and records audit log entries."""
    await bootstrap_primary_owner(
        email="admin@servicepulse.uz",
        full_name="Platform Owner",
        password="AdminPass2026!",
        force=True,
        db_session=test_db,
    )
    owner_token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")

    # Create request
    create_resp = await client.post(
        "/api/v1/access-requests",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "request_type": "employee_access",
            "applicant_email": "rejection.test@example.com",
            "applicant_full_name": "Rejection Test",
            "organization_id": 1,
            "justification": "Testing rejection mechanics",
        },
    )
    req_id = create_resp.json()["id"]

    # Empty rejection reason -> 422
    rej_fail = await client.post(
        f"/api/v1/access-requests/{req_id}/reject",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"reason": "  "},
    )
    assert rej_fail.status_code == 422

    # Valid rejection
    rej_success = await client.post(
        f"/api/v1/access-requests/{req_id}/reject",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"reason": "Applicant background verification inconclusive."},
    )
    assert rej_success.status_code == 200
    data = rej_success.json()
    assert data["status"] == "rejected"
    assert data["rejection_reason"] == "Applicant background verification inconclusive."

    # Verify audit log
    audit_res = await test_db.execute(
        select(AuditLog).where(
            AuditLog.action == "access_request_rejected",
            AuditLog.target_id == str(req_id),
        )
    )
    audit = audit_res.scalar_one_or_none()
    assert audit is not None
    assert audit.status == "success"
    assert "inconclusive" in audit.details


@pytest.mark.asyncio
async def test_concurrency_approval_resilience(client: AsyncClient, test_db: AsyncSession):
    """Verify concurrent approval requests on the same access request cannot succeed twice."""
    await bootstrap_primary_owner(
        email="admin@servicepulse.uz",
        full_name="Platform Owner",
        password="AdminPass2026!",
        force=True,
        db_session=test_db,
    )
    owner_token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")

    create_resp = await client.post(
        "/api/v1/access-requests",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "request_type": "support_access",
            "applicant_email": "concurrent.applicant@example.com",
            "applicant_full_name": "Concurrent Applicant",
            "organization_id": 1,
            "justification": "Testing race condition handling",
        },
    )
    req_id = create_resp.json()["id"]

    # Launch two concurrent approval requests
    async def approve_call():
        return await client.post(
            f"/api/v1/access-requests/{req_id}/approve",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

    res1, res2 = await asyncio.gather(approve_call(), approve_call(), return_exceptions=True)

    status_codes = sorted([res1.status_code, res2.status_code])
    # Exactly one must succeed (200), and the second must be rejected (400 - "Cannot approve request with status 'approved'")
    assert status_codes == [200, 400], f"Concurrency unexpected statuses: {status_codes}"
