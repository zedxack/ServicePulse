"""
ServicePulse - Multi-Tenant Isolation & 5 Role-Based Dashboards Integration Tests
Verifies:
1. Strict cross-tenant resource isolation (devices, incidents, tickets, users).
2. Tenant Admin boundary protections (cannot access another organization's data).
3. Platform Super Admin global operations & audits.
4. Five distinct role-based dashboard experiences:
   - Platform Super Admin (/api/v1/dashboard/platform)
   - Company Admin (/api/v1/dashboard/company)
   - SysAdmin / IT Support (/api/v1/dashboard/sysadmin)
   - Executive / CEO (/api/v1/dashboard/executive)
   - Employee (/api/v1/dashboard/employee)
Author: Muhammadyusuf Usmonov
"""
import pytest
from httpx import AsyncClient


async def get_auth_token(client: AsyncClient, email: str, password: str) -> str:
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_organization_management_and_rbac(client: AsyncClient):
    # 1. Login as Platform Super Admin
    super_token = await get_auth_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    super_headers = {"Authorization": f"Bearer {super_token}"}

    # Verify initial list has demo-org
    res_list = await client.get("/api/v1/organizations", headers=super_headers)
    assert res_list.status_code == 200
    orgs = res_list.json()
    assert len(orgs) >= 1
    assert any(o["slug"] == "demo-org" for o in orgs)

    # Create Organization 2
    res_create = await client.post(
        "/api/v1/organizations",
        json={
            "name": "Samarkand Data Center Branch",
            "slug": "samarkand-dc",
            "domain": "samarkand.servicepulse.uz",
            "max_devices": 50,
        },
        headers=super_headers,
    )
    assert res_create.status_code == 201
    org2_data = res_create.json()
    org2_id = org2_data["id"]
    assert org2_data["slug"] == "samarkand-dc"
    assert org2_data["max_devices"] == 50

    # 2. Login as Company Admin of Org 1
    comp_token = await get_auth_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    comp_headers = {"Authorization": f"Bearer {comp_token}"}

    # Tenant admin cannot list all organizations
    res_forbidden_list = await client.get("/api/v1/organizations", headers=comp_headers)
    assert res_forbidden_list.status_code == 403

    # Tenant admin cannot create organizations
    res_forbidden_create = await client.post(
        "/api/v1/organizations",
        json={"name": "Illegal Org", "slug": "illegal-org", "max_devices": 10},
        headers=comp_headers,
    )
    assert res_forbidden_create.status_code == 403

    # Tenant admin can read own organization
    res_own_org = await client.get("/api/v1/organizations/1", headers=comp_headers)
    assert res_own_org.status_code == 200
    assert res_own_org.json()["slug"] == "demo-org"

    # Tenant admin CANNOT read Org 2
    res_other_org = await client.get(f"/api/v1/organizations/{org2_id}", headers=comp_headers)
    assert res_other_org.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_resource_isolation(client: AsyncClient):
    super_token = await get_auth_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    super_headers = {"Authorization": f"Bearer {super_token}"}

    # 1. Create Organization B
    res_org2 = await client.post(
        "/api/v1/organizations",
        json={"name": "Fergana Regional Node", "slug": "fergana-node", "max_devices": 30},
        headers=super_headers,
    )
    assert res_org2.status_code == 201
    org2_id = res_org2.json()["id"]

    # 2. Create User for Organization B
    res_user2 = await client.post(
        "/api/v1/auth/users",
        json={
            "email": "fergana_admin@servicepulse.uz",
            "password": "FerganaAdmin2026!",
            "full_name": "Fergana Administrator",
            "organization_id": org2_id,
            "role_names": ["company_admin"],
        },
        headers=super_headers,
    )
    assert res_user2.status_code == 201
    user2_data = res_user2.json()
    assert user2_data["organization_id"] == org2_id

    # 3. Create Building & Device for Organization B
    res_bld2 = await client.post(
        "/api/v1/inventory/buildings",
        json={
            "name": "Fergana Main Building",
            "code": "BLD-FERGANA",
            "organization_id": org2_id,
        },
        headers=super_headers,
    )
    assert res_bld2.status_code == 201
    assert res_bld2.json()["id"] > 0

    res_dev2 = await client.post(
        "/api/v1/inventory/devices",
        json={
            "name": "SRV-FERGANA-01",
            "hostname": "srv-fergana-01.local",
            "ip_address": "10.20.0.10",
            "device_type": "server",
            "organization_id": org2_id,
        },
        headers=super_headers,
    )
    assert res_dev2.status_code == 201
    dev2_id = res_dev2.json()["id"]

    # 4. Create Incident in Org 2
    res_inc2 = await client.post(
        "/api/v1/incidents",
        json={
            "title": "Fergana Core Switch Latency High",
            "description": "Ping round trip exceeding 150ms",
            "severity": "warning",
            "device_id": dev2_id,
            "organization_id": org2_id,
        },
        headers=super_headers,
    )
    assert res_inc2.status_code == 201
    inc2_id = res_inc2.json()["id"]

    # 5. Login as Org 1 Company Admin
    org1_token = await get_auth_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    org1_headers = {"Authorization": f"Bearer {org1_token}"}

    # Isolation Check A: Devices
    # Org 1 admin lists devices -> MUST NOT see SRV-FERGANA-01
    res_org1_devs = await client.get("/api/v1/inventory/devices", headers=org1_headers)
    assert res_org1_devs.status_code == 200
    dev_names = [d["name"] for d in res_org1_devs.json()]
    assert "SRV-FERGANA-01" not in dev_names

    # Direct ID lookup of Org 2 device returns 404 (preventing enumeration)
    res_dev2_cross = await client.get(f"/api/v1/inventory/devices/{dev2_id}", headers=org1_headers)
    assert res_dev2_cross.status_code == 404

    # Isolation Check B: Incidents
    res_org1_incidents = await client.get("/api/v1/incidents", headers=org1_headers)
    assert res_org1_incidents.status_code == 200
    inc_ids = [i["id"] for i in res_org1_incidents.json()["items"]]
    assert inc2_id not in inc_ids

    res_inc2_cross = await client.get(f"/api/v1/incidents/{inc2_id}", headers=org1_headers)
    assert res_inc2_cross.status_code == 404

    # Isolation Check C: Users
    res_org1_users = await client.get("/api/v1/auth/users", headers=org1_headers)
    assert res_org1_users.status_code == 200
    user_emails = [u["email"] for u in res_org1_users.json()]
    assert "fergana_admin@servicepulse.uz" not in user_emails

    # 6. Verify Org 2 Admin sees their own data
    org2_token = await get_auth_token(client, "fergana_admin@servicepulse.uz", "FerganaAdmin2026!")
    org2_headers = {"Authorization": f"Bearer {org2_token}"}

    res_org2_devs = await client.get("/api/v1/inventory/devices", headers=org2_headers)
    assert res_org2_devs.status_code == 200
    org2_names = [d["name"] for d in res_org2_devs.json()]
    assert "SRV-FERGANA-01" in org2_names

    # Org 2 Admin cannot access Org 1 building
    res_cross_bld = await client.get("/api/v1/inventory/buildings/1", headers=org2_headers)
    assert res_cross_bld.status_code == 404


@pytest.mark.asyncio
async def test_five_role_based_dashboards(client: AsyncClient):
    # Retrieve tokens for all 5 roles
    super_tok = await get_auth_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    comp_tok = await get_auth_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    it_tok = await get_auth_token(client, "support@servicepulse.uz", "SupportPass2026!")
    exec_tok = await get_auth_token(client, "executive@servicepulse.uz", "ExecutivePass2026!")
    emp_tok = await get_auth_token(client, "employee@servicepulse.uz", "EmployeePass2026!")

    # -------------------------------------------------------------------------
    # 1. PLATFORM SUPER ADMIN DASHBOARD
    # -------------------------------------------------------------------------
    res_platform = await client.get("/api/v1/dashboard/platform", headers={"Authorization": f"Bearer {super_tok}"})
    assert res_platform.status_code == 200
    p_data = res_platform.json()
    assert "total_organizations" in p_data
    assert p_data["total_organizations"] >= 1
    assert "platform_health_status" in p_data
    assert "recent_global_audits" in p_data

    # Company Admin and Employee cannot access platform dashboard
    res_p_comp = await client.get("/api/v1/dashboard/platform", headers={"Authorization": f"Bearer {comp_tok}"})
    assert res_p_comp.status_code == 403

    res_p_emp = await client.get("/api/v1/dashboard/platform", headers={"Authorization": f"Bearer {emp_tok}"})
    assert res_p_emp.status_code == 403

    # -------------------------------------------------------------------------
    # 2. COMPANY ADMIN DASHBOARD
    # -------------------------------------------------------------------------
    res_company = await client.get("/api/v1/dashboard/company", headers={"Authorization": f"Bearer {comp_tok}"})
    assert res_company.status_code == 200
    c_data = res_company.json()
    assert c_data["organization_name"] == "Example Corporation"
    assert "device_utilization_percent" in c_data
    assert "total_buildings" in c_data
    assert "recent_org_audits" in c_data

    res_c_emp = await client.get("/api/v1/dashboard/company", headers={"Authorization": f"Bearer {emp_tok}"})
    assert res_c_emp.status_code == 403

    # -------------------------------------------------------------------------
    # 3. SYSADMIN / IT SUPPORT DASHBOARD
    # -------------------------------------------------------------------------
    res_sys = await client.get("/api/v1/dashboard/sysadmin", headers={"Authorization": f"Bearer {it_tok}"})
    assert res_sys.status_code == 200
    s_data = res_sys.json()
    assert "online_devices" in s_data
    assert "active_incidents" in s_data
    assert "telemetry_summary" in s_data
    assert "devices_by_building" in s_data

    res_s_emp = await client.get("/api/v1/dashboard/sysadmin", headers={"Authorization": f"Bearer {emp_tok}"})
    assert res_s_emp.status_code == 403

    # -------------------------------------------------------------------------
    # 4. CEO / EXECUTIVE DASHBOARD
    # -------------------------------------------------------------------------
    res_exec = await client.get("/api/v1/dashboard/executive", headers={"Authorization": f"Bearer {exec_tok}"})
    assert res_exec.status_code == 200
    e_data = res_exec.json()
    assert "infrastructure_availability_percent" in e_data
    assert "sla_achievement_percent" in e_data
    assert "mttd_status" in e_data
    assert "mttr_status" in e_data
    assert "top_risk_devices" in e_data
    assert "incident_trends" in e_data

    # Test alias /ceo
    res_ceo = await client.get("/api/v1/dashboard/ceo", headers={"Authorization": f"Bearer {exec_tok}"})
    assert res_ceo.status_code == 200
    assert res_ceo.json()["infrastructure_availability_percent"] == e_data["infrastructure_availability_percent"]

    res_e_emp = await client.get("/api/v1/dashboard/executive", headers={"Authorization": f"Bearer {emp_tok}"})
    assert res_e_emp.status_code == 403

    # -------------------------------------------------------------------------
    # 5. EMPLOYEE DASHBOARD
    # -------------------------------------------------------------------------
    # First submit a ticket and software request as employee to populate counters
    await client.post(
        "/api/v1/tickets",
        json={"title": "Printer Jam in Lab 204", "description": "Paper tray stuck", "priority": "medium"},
        headers={"Authorization": f"Bearer {emp_tok}"},
    )

    res_emp = await client.get("/api/v1/dashboard/employee", headers={"Authorization": f"Bearer {emp_tok}"})
    assert res_emp.status_code == 200
    emp_data = res_emp.json()
    assert emp_data["user_name"] == "Alex Morgan"
    assert emp_data["open_tickets_count"] >= 1
    assert len(emp_data["recent_tickets"]) >= 1
    assert "recent_software_requests" in emp_data


@pytest.mark.asyncio
async def test_primary_dashboard_routing_claim(client: AsyncClient):
    # Verify login response primary_dashboard matches expected role routing
    logins = [
        ("admin@servicepulse.uz", "AdminPass2026!", "platform"),
        ("company_admin@servicepulse.uz", "CompanyAdminPass2026!", "company"),
        ("support@servicepulse.uz", "SupportPass2026!", "sysadmin"),
        ("executive@servicepulse.uz", "ExecutivePass2026!", "executive"),
        ("employee@servicepulse.uz", "EmployeePass2026!", "employee"),
    ]

    for email, pw, expected_dash in logins:
        res = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
        assert res.status_code == 200
        data = res.json()
        assert data["primary_dashboard"] == expected_dash, f"Expected {expected_dash} for {email}, got {data['primary_dashboard']}"

        # Also verify GET /auth/me returns the same primary_dashboard
        tok = data["access_token"]
        res_me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"})
        assert res_me.status_code == 200
        assert res_me.json()["primary_dashboard"] == expected_dash
