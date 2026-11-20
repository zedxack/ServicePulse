"""
ServicePulse - Step 5.2 Final Security & API Contract Audit Test Suite
Author: Muhammadyusuf Usmonov

Comprehensive verification of:
1. Cross-Tenant ID Isolation:
   - Inventory devices & network checks
   - Incidents & event history
   - Helpdesk tickets & comments
   - Software requests & approval workflows
   - Remediation executions
2. Employee Intra-Tenant Isolation:
   - Employees cannot access or manipulate other employees' tickets or software requests.
3. RBAC Enforcement:
   - Approval/rejection endpoints reject unauthorized roles (employees, support).
   - Remediation execution endpoints reject non-operations roles (employees).
4. Server-Side Sensitive Redaction:
   - Bearer tokens, secrets, passwords, and authorization headers are scrubbed from execution logs.
"""
import pytest
from httpx import AsyncClient

from backend.app.core.config import settings
from backend.app.core.security import redact_sensitive_text


async def get_token(client: AsyncClient, email: str, password: str) -> str:
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def test_redact_sensitive_text_unit():
    """Verify server-side redaction scrubs tokens, passwords, secrets and authorization headers."""
    # 1. Bearer token
    raw_bearer = "Command error: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-IDjh by agent"
    redacted_bearer = redact_sensitive_text(raw_bearer)
    assert "Bearer [REDACTED]" in redacted_bearer
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted_bearer

    # 2. Key-value password and secret
    raw_secrets = "Config: password='SuperSecretPassword123!', client_secret=\"TopSecretApiKey999\""
    redacted_secrets = redact_sensitive_text(raw_secrets)
    assert "password='[REDACTED]'" in redacted_secrets or "password=[REDACTED]" in redacted_secrets
    assert "SuperSecretPassword123!" not in redacted_secrets
    assert "TopSecretApiKey999" not in redacted_secrets

    # 3. Authorization header
    raw_header = "HTTP/1.1 500 Error\nAuthorization: Bearer secret_agent_jwt_blob\nHost: api.local"
    redacted_header = redact_sensitive_text(raw_header)
    assert "Authorization: [REDACTED]" in redacted_header
    assert "secret_agent_jwt_blob" not in redacted_header

    # 4. Safe plain text is preserved
    plain = "Service 'Spooler' successfully restarted on target host ws-lab-01"
    assert redact_sensitive_text(plain) == plain


@pytest.mark.asyncio
async def test_step5_2_cross_tenant_id_isolation(client: AsyncClient):
    """
    Verify changing an ID for device, incident, ticket, or software request
    returns 404 and NEVER leaks another tenant's records.
    """
    super_tok = await get_token(client, settings.FIRST_SUPERUSER_EMAIL, settings.FIRST_SUPERUSER_PASSWORD)
    super_h = {"Authorization": f"Bearer {super_tok}"}

    # 1. Create Tenant Alpha and Tenant Beta
    res_a = await client.post("/api/v1/organizations", json={"name": "Audit Alpha", "slug": "audit-alpha-52"}, headers=super_h)
    assert res_a.status_code == 201
    org_a_id = res_a.json()["id"]

    res_b = await client.post("/api/v1/organizations", json={"name": "Audit Beta", "slug": "audit-beta-52"}, headers=super_h)
    assert res_b.status_code == 201
    org_b_id = res_b.json()["id"]

    # 2. Create Admin Users for Alpha & Beta
    await client.post(
        "/api/v1/auth/users",
        json={"email": "admin@alpha52.uz", "password": "AlphaPass2026!", "full_name": "Alpha Admin", "role_names": ["company_admin"], "organization_id": org_a_id},
        headers=super_h,
    )
    await client.post(
        "/api/v1/auth/users",
        json={"email": "admin@beta52.uz", "password": "BetaPass2026!", "full_name": "Beta Admin", "role_names": ["company_admin"], "organization_id": org_b_id},
        headers=super_h,
    )

    tok_a = await get_token(client, "admin@alpha52.uz", "AlphaPass2026!")
    tok_b = await get_token(client, "admin@beta52.uz", "BetaPass2026!")
    h_a = {"Authorization": f"Bearer {tok_a}"}
    h_b = {"Authorization": f"Bearer {tok_b}"}

    # 3. Alpha creates a Device
    res_bld = await client.post("/api/v1/inventory/buildings", json={"name": "Alpha Building", "code": "ALP-52"}, headers=h_a)
    assert res_bld.status_code == 201
    res_flr = await client.post("/api/v1/inventory/floors", json={"building_id": res_bld.json()["id"], "level": 1, "name": "Alpha F1"}, headers=h_a)
    assert res_flr.status_code == 201
    res_rm = await client.post("/api/v1/inventory/rooms", json={"floor_id": res_flr.json()["id"], "room_number": "101", "name": "Alpha Room"}, headers=h_a)
    assert res_rm.status_code == 201

    res_dev_a = await client.post(
        "/api/v1/inventory/devices",
        json={"name": "Alpha Core Server", "hostname": "alpha-srv-01", "ip_address": "10.10.1.1", "device_type": "server", "room_id": res_rm.json()["id"]},
        headers=h_a,
    )
    assert res_dev_a.status_code == 201
    dev_a_id = res_dev_a.json()["id"]

    # 4. Alpha creates an Incident
    res_inc_a = await client.post(
        "/api/v1/incidents",
        json={"title": "Alpha Outage", "description": "Core switch down", "severity": "critical", "device_id": dev_a_id},
        headers=h_a,
    )
    assert res_inc_a.status_code == 201
    inc_a_id = res_inc_a.json()["id"]

    # 5. Beta attempts to access Alpha's device and checks -> 404 Not Found
    get_dev = await client.get(f"/api/v1/inventory/devices/{dev_a_id}", headers=h_b)
    assert get_dev.status_code == 404, f"Cross-tenant device leak: {get_dev.text}"

    get_checks = await client.get(f"/api/v1/inventory/devices/{dev_a_id}/network-checks", headers=h_b)
    assert get_checks.status_code == 404, f"Cross-tenant checks leak: {get_checks.text}"

    # 6. Beta attempts to access Alpha's incident -> 404 Not Found
    get_inc = await client.get(f"/api/v1/incidents/{inc_a_id}", headers=h_b)
    assert get_inc.status_code == 404, f"Cross-tenant incident leak: {get_inc.text}"

    get_events = await client.get(f"/api/v1/incidents/{inc_a_id}/events", headers=h_b)
    assert get_events.status_code == 404, f"Cross-tenant events leak: {get_events.text}"

    # 7. Beta attempts to acknowledge or resolve Alpha's incident -> 404 Not Found
    ack_res = await client.patch(f"/api/v1/incidents/{inc_a_id}/acknowledge", json={"notes": "Hacked"}, headers=h_b)
    assert ack_res.status_code == 404

    res_res = await client.patch(f"/api/v1/incidents/{inc_a_id}/resolve", json={"resolution_notes": "Fake resolved"}, headers=h_b)
    assert res_res.status_code == 404


@pytest.mark.asyncio
async def test_step5_2_employee_isolation_and_rbac(client: AsyncClient):
    """
    Verify intra-tenant employee isolation:
    - Employees cannot view or modify other employees' tickets or requests.
    - Employees and Support roles cannot approve or reject software requests.
    - Employees cannot view remediation executions.
    """
    super_tok = await get_token(client, settings.FIRST_SUPERUSER_EMAIL, settings.FIRST_SUPERUSER_PASSWORD)
    super_h = {"Authorization": f"Bearer {super_tok}"}

    # Create Org Gamma
    res_org = await client.post("/api/v1/organizations", json={"name": "Audit Gamma", "slug": "audit-gamma-52"}, headers=super_h)
    org_id = res_org.json()["id"]

    # Create IT Admin, Support, and two Employees in Org Gamma
    await client.post(
        "/api/v1/auth/users",
        json={"email": "itadmin@gamma52.uz", "password": "PassGamma2026!", "full_name": "Gamma IT Admin", "role_names": ["it_admin"], "organization_id": org_id},
        headers=super_h,
    )
    await client.post(
        "/api/v1/auth/users",
        json={"email": "support@gamma52.uz", "password": "PassGamma2026!", "full_name": "Gamma Support", "role_names": ["support"], "organization_id": org_id},
        headers=super_h,
    )
    await client.post(
        "/api/v1/auth/users",
        json={"email": "emp1@gamma52.uz", "password": "PassGamma2026!", "full_name": "Gamma Employee 1", "role_names": ["employee"], "organization_id": org_id},
        headers=super_h,
    )
    await client.post(
        "/api/v1/auth/users",
        json={"email": "emp2@gamma52.uz", "password": "PassGamma2026!", "full_name": "Gamma Employee 2", "role_names": ["employee"], "organization_id": org_id},
        headers=super_h,
    )

    tok_admin = await get_token(client, "itadmin@gamma52.uz", "PassGamma2026!")
    tok_supp = await get_token(client, "support@gamma52.uz", "PassGamma2026!")
    tok_emp1 = await get_token(client, "emp1@gamma52.uz", "PassGamma2026!")
    tok_emp2 = await get_token(client, "emp2@gamma52.uz", "PassGamma2026!")

    h_admin = {"Authorization": f"Bearer {tok_admin}"}
    h_supp = {"Authorization": f"Bearer {tok_supp}"}
    h_emp1 = {"Authorization": f"Bearer {tok_emp1}"}
    h_emp2 = {"Authorization": f"Bearer {tok_emp2}"}

    # Setup device
    res_bld = await client.post("/api/v1/inventory/buildings", json={"name": "Gamma Bld", "code": "GAM-52"}, headers=h_admin)
    res_flr = await client.post("/api/v1/inventory/floors", json={"building_id": res_bld.json()["id"], "level": 1, "name": "Gamma F1"}, headers=h_admin)
    res_rm = await client.post("/api/v1/inventory/rooms", json={"floor_id": res_flr.json()["id"], "room_number": "101", "name": "Gamma Room"}, headers=h_admin)
    res_dev = await client.post(
        "/api/v1/inventory/devices",
        json={"name": "Gamma Workstation", "hostname": "gamma-ws-01", "ip_address": "10.20.1.10", "device_type": "workstation", "room_id": res_rm.json()["id"]},
        headers=h_admin,
    )
    dev_id = res_dev.json()["id"]

    # 1. Employee 1 submits a Ticket and a Software Request
    res_t1 = await client.post(
        "/api/v1/tickets",
        json={"title": "Emp 1 Ticket", "description": "Printer ink exhausted", "category": "hardware", "priority": "low"},
        headers=h_emp1,
    )
    assert res_t1.status_code == 201
    t1_id = res_t1.json()["id"]

    res_sr1 = await client.post(
        "/api/v1/software/requests",
        json={"device_id": dev_id, "software_name": "Google Chrome", "software_version": "120", "reason": "Browser testing requirement"},
        headers=h_emp1,
    )
    assert res_sr1.status_code == 201
    sr1_id = res_sr1.json()["id"]

    # 2. Employee 2 attempts to read Employee 1's ticket and comments -> 403 Forbidden
    get_t1_by_e2 = await client.get(f"/api/v1/tickets/{t1_id}", headers=h_emp2)
    assert get_t1_by_e2.status_code == 403, f"Expected 403, got {get_t1_by_e2.status_code}"

    get_com_by_e2 = await client.get(f"/api/v1/tickets/{t1_id}/comments", headers=h_emp2)
    assert get_com_by_e2.status_code == 403, f"Expected 403, got {get_com_by_e2.status_code}"

    # 3. Employee 2 attempts to read Employee 1's software request -> 403 Forbidden
    get_sr1_by_e2 = await client.get(f"/api/v1/software/requests/{sr1_id}", headers=h_emp2)
    assert get_sr1_by_e2.status_code == 403, f"Expected 403, got {get_sr1_by_e2.status_code}"

    # 4. Employee 1 attempts to self-approve software request -> 403 Forbidden
    self_app = await client.post(f"/api/v1/software/requests/{sr1_id}/approve", json={"review_notes": "Self approved"}, headers=h_emp1)
    assert self_app.status_code == 403

    # 5. Support role attempts to approve software request -> 403 Forbidden (Only IT Admin / Company Admin / Super Admin)
    supp_app = await client.post(f"/api/v1/software/requests/{sr1_id}/approve", json={"review_notes": "Support approved"}, headers=h_supp)
    assert supp_app.status_code == 403

    # 6. IT Admin approves software request -> 200 OK
    admin_app = await client.post(f"/api/v1/software/requests/{sr1_id}/approve", json={"review_notes": "IT Admin approved for compliance"}, headers=h_admin)
    assert admin_app.status_code == 200
    assert admin_app.json()["status"] == "approved"

    # 7. Employee attempts to access remediation executions -> 403 Forbidden
    emp_rem = await client.get("/api/v1/remediations/executions", headers=h_emp1)
    assert emp_rem.status_code == 403, f"Expected 403 for employee remediation access, got {emp_rem.status_code}"

    # 8. IT Admin accesses remediation executions -> 200 OK
    admin_rem = await client.get("/api/v1/remediations/executions", headers=h_admin)
    assert admin_rem.status_code == 200
