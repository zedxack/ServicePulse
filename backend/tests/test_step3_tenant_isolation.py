"""
ServicePulse - Step 3 Multi-Tenant Isolation & Security Test Suite
Verifies strict organization boundaries and cross-tenant access rejection for:
1. NetworkCheck queries and on-demand probes
2. Device monitoring status and outage visibility
3. MaintenanceWindow creation and listing
4. RemediationRule creation, listing, and direct retrieval
5. RemediationExecution lifecycle, approval, rejection, and verification
6. Nested resource cross-ownership validation (Rule, Incident, Device)
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from backend.app.workers.probe_engine import ProbeEngine


async def get_token(client: AsyncClient, email: str, password: str) -> str:
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_step3_network_and_monitoring_tenant_isolation(client: AsyncClient):
    """
    Verify cross-tenant isolation for NetworkChecks, Probes, Device Status, and Maintenance Windows.
    Org A cannot see, probe, or manage Org B's devices or monitoring infrastructure.
    """
    super_tok = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    comp_a_tok = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")

    super_h = {"Authorization": f"Bearer {super_tok}"}
    comp_a_h = {"Authorization": f"Bearer {comp_a_tok}"}

    # 1. Create Organization B
    res_org_b = await client.post(
        "/api/v1/organizations",
        json={"name": "Org B Monitoring Corp", "slug": "org-b-mon", "max_devices": 15},
        headers=super_h,
    )
    assert res_org_b.status_code == 201
    org_b_id = res_org_b.json()["id"]

    # 2. Create Org B Admin
    res_b_user = await client.post(
        "/api/v1/auth/users",
        json={
            "email": "admin@orgbmon.uz",
            "password": "PasswordOrgB2026!",
            "full_name": "Org B Admin",
            "role_names": ["company_admin"],
            "organization_id": org_b_id,
        },
        headers=super_h,
    )
    assert res_b_user.status_code == 201

    b_admin_tok = await get_token(client, "admin@orgbmon.uz", "PasswordOrgB2026!")
    b_admin_h = {"Authorization": f"Bearer {b_admin_tok}"}

    # 3. Create Org B Inventory (Building, Floor, Room, Device)
    bld_b = (await client.post(
        "/api/v1/inventory/buildings",
        json={"name": "Org B HQ", "code": "ORGB-HQ"},
        headers=b_admin_h,
    )).json()

    flr_b = (await client.post(
        "/api/v1/inventory/floors",
        json={"building_id": bld_b["id"], "level": 1, "name": "Floor 1"},
        headers=b_admin_h,
    )).json()

    rm_b = (await client.post(
        "/api/v1/inventory/rooms",
        json={"floor_id": flr_b["id"], "room_number": "101", "name": "Data Center"},
        headers=b_admin_h,
    )).json()

    dev_b = (await client.post(
        "/api/v1/inventory/devices",
        json={
            "room_id": rm_b["id"],
            "name": "Org B Gateway Firewall",
            "hostname": "fw01.orgb.local",
            "ip_address": "10.10.10.1",
            "device_type": "firewall",
        },
        headers=b_admin_h,
    )).json()
    org_b_dev_id = dev_b["id"]

    # 4. Org B triggers an on-demand probe on its own device (simulation override enabled)
    ProbeEngine.set_simulation_override(True)
    r_b_probe = await client.post(
        f"/api/v1/network/devices/{org_b_dev_id}/probe",
        json={"check_type": "icmp_ping"},
        headers=b_admin_h,
    )
    ProbeEngine.set_simulation_override(None)
    assert r_b_probe.status_code == 200

    # 5. Org A attempts cross-tenant access on Org B's device
    # (a) Org A cannot probe Org B device -> 404
    r_a_probe = await client.post(
        f"/api/v1/network/devices/{org_b_dev_id}/probe",
        json={"check_type": "icmp_ping"},
        headers=comp_a_h,
    )
    assert r_a_probe.status_code == 404

    # (b) Org A cannot get device checks for Org B device -> 404
    r_a_dev_checks = await client.get(
        f"/api/v1/network/devices/{org_b_dev_id}/checks",
        headers=comp_a_h,
    )
    assert r_a_dev_checks.status_code == 404

    # (c) Org A cannot get device monitoring status for Org B device -> 404
    r_a_dev_status = await client.get(
        f"/api/v1/network/devices/{org_b_dev_id}/status",
        headers=comp_a_h,
    )
    assert r_a_dev_status.status_code == 404

    # (d) Org A checks general checks list: must NOT contain Org B device checks
    r_a_all_checks = await client.get("/api/v1/network/checks", headers=comp_a_h)
    assert r_a_all_checks.status_code == 200
    for chk in r_a_all_checks.json():
        assert chk["device_id"] != org_b_dev_id

    # 6. Maintenance Windows Cross-Tenant Isolation
    now = datetime.now(timezone.utc)
    # Org B creates a maintenance window
    r_maint_b = await client.post(
        "/api/v1/network/maintenance",
        json={
            "title": "Org B Core Network Maintenance",
            "description": "Upgrading core switch firmware",
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=3)).isoformat(),
            "device_id": org_b_dev_id,
        },
        headers=b_admin_h,
    )
    assert r_maint_b.status_code == 201
    maint_b_id = r_maint_b.json()["id"]

    # Org A lists maintenance windows: must NOT contain Org B's maintenance window
    r_a_maint_list = await client.get("/api/v1/network/maintenance", headers=comp_a_h)
    assert r_a_maint_list.status_code == 200
    for mw in r_a_maint_list.json():
        assert mw["id"] != maint_b_id

    # Org A attempts to create maintenance window targeting Org B device -> 404
    r_a_create_maint = await client.post(
        "/api/v1/network/maintenance",
        json={
            "title": "Unauthorized Maintenance Window",
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=3)).isoformat(),
            "device_id": org_b_dev_id,
        },
        headers=comp_a_h,
    )
    assert r_a_create_maint.status_code == 404


@pytest.mark.asyncio
async def test_step3_remediation_tenant_isolation_and_ownership(client: AsyncClient):
    """
    Verify cross-tenant isolation and parent-resource ownership enforcement for:
    - RemediationRule creation and retrieval
    - RemediationExecution creation, retrieval, approval, rejection, and verification
    - Cross-tenant injection rejection (Org A cannot execute Org B's rule on Org B's incident)
    """
    super_tok = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    comp_a_tok = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")

    super_h = {"Authorization": f"Bearer {super_tok}"}
    comp_a_h = {"Authorization": f"Bearer {comp_a_tok}"}

    # 1. Create Organization B
    res_org_b = await client.post(
        "/api/v1/organizations",
        json={"name": "Org B Remediation Corp", "slug": "org-b-rem", "max_devices": 10},
        headers=super_h,
    )
    assert res_org_b.status_code == 201
    org_b_id = res_org_b.json()["id"]

    # 2. Create Org B Admin
    res_b_user = await client.post(
        "/api/v1/auth/users",
        json={
            "email": "admin@orgbrem.uz",
            "password": "PasswordOrgB2026!",
            "full_name": "Org B Admin",
            "role_names": ["company_admin"],
            "organization_id": org_b_id,
        },
        headers=super_h,
    )
    assert res_b_user.status_code == 201

    b_admin_tok = await get_token(client, "admin@orgbrem.uz", "PasswordOrgB2026!")
    b_admin_h = {"Authorization": f"Bearer {b_admin_tok}"}

    # 3. Org B creates a Remediation Rule
    r_rule_b = await client.post(
        "/api/v1/remediations/rules",
        json={
            "name": "Org B Auto-Restart Spooler",
            "trigger_condition": "spooler_crash",
            "action_name": "restart_service",
            "action_parameters": '{"service_name": "Spooler"}',
            "requires_approval": True,
        },
        headers=b_admin_h,
    )
    assert r_rule_b.status_code == 201
    rule_b_id = r_rule_b.json()["id"]

    # 4. Org B creates an Incident
    r_inc_b = await client.post(
        "/api/v1/incidents",
        json={
            "title": "Org B Spooler Outage",
            "description": "Print spooler failure on Org B host",
            "severity": "critical",
        },
        headers=b_admin_h,
    )
    assert r_inc_b.status_code == 201
    inc_b_id = r_inc_b.json()["id"]

    # 5. Org B creates a Remediation Execution
    r_exec_b = await client.post(
        "/api/v1/remediations/executions",
        json={"rule_id": rule_b_id, "incident_id": inc_b_id},
        headers=b_admin_h,
    )
    assert r_exec_b.status_code == 201
    exec_b_id = r_exec_b.json()["id"]
    assert r_exec_b.json()["status"] == "pending_approval"

    # 6. Verify Org A CANNOT access Org B's Remediation Rules
    # (a) Org A listing rules does not include Org B's rule
    r_a_rules = await client.get("/api/v1/remediations/rules", headers=comp_a_h)
    assert r_a_rules.status_code == 200
    for r in r_a_rules.json():
        assert r["id"] != rule_b_id

    # (b) Org A direct access to Org B rule -> 404
    r_a_get_rule = await client.get(f"/api/v1/remediations/rules/{rule_b_id}", headers=comp_a_h)
    assert r_a_get_rule.status_code == 404

    # 7. Verify Org A CANNOT access Org B's Remediation Executions
    # (a) Org A listing executions does not include Org B's execution
    r_a_execs = await client.get("/api/v1/remediations/executions", headers=comp_a_h)
    assert r_a_execs.status_code == 200
    for e in r_a_execs.json():
        assert e["id"] != exec_b_id

    # (b) Org A direct access to Org B execution -> 404
    r_a_get_exec = await client.get(f"/api/v1/remediations/executions/{exec_b_id}", headers=comp_a_h)
    assert r_a_get_exec.status_code == 404

    # (c) Org A attempts to approve Org B execution -> 404
    r_a_approve = await client.post(
        f"/api/v1/remediations/executions/{exec_b_id}/approve",
        json={"decision": "approved", "review_notes": "Unauthorized approval attempt"},
        headers=comp_a_h,
    )
    assert r_a_approve.status_code == 404

    # (d) Org A attempts to reject Org B execution -> 404
    r_a_reject = await client.post(
        f"/api/v1/remediations/executions/{exec_b_id}/reject",
        json={"decision": "rejected", "review_notes": "Unauthorized rejection attempt"},
        headers=comp_a_h,
    )
    assert r_a_reject.status_code == 404

    # (e) Org A attempts to verify Org B execution -> 404
    r_a_verify = await client.post(
        f"/api/v1/remediations/executions/{exec_b_id}/verify",
        headers=comp_a_h,
    )
    assert r_a_verify.status_code == 404

    # 8. Cross-Tenant Creation Injection Rejection:
    # Org A attempts to trigger an execution referencing Org B's rule and Org B's incident -> 404
    r_a_inject = await client.post(
        "/api/v1/remediations/executions",
        json={"rule_id": rule_b_id, "incident_id": inc_b_id},
        headers=comp_a_h,
    )
    assert r_a_inject.status_code == 404

    # 9. Legitimate Org B Admin CAN approve own execution -> 200 OK
    r_b_approve = await client.post(
        f"/api/v1/remediations/executions/{exec_b_id}/approve",
        json={"decision": "approved", "review_notes": "Authorized Org B Admin Approval"},
        headers=b_admin_h,
    )
    assert r_b_approve.status_code == 200
    assert r_b_approve.json()["status"] == "executing"
