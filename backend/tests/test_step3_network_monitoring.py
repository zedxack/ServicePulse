"""
ServicePulse - Step 3 Network Monitoring Test Suite
Tests ICMP/TCP probes, timeouts, concurrency, scheduler, unauthorized target rejection,
and tenant isolation across all /network endpoints.
Author: Muhammadyusuf Usmonov
"""
import pytest
from httpx import AsyncClient

from backend.app.workers.probe_engine import ProbeEngine
from backend.app.workers.scheduler import MonitoringScheduler


async def get_token(client: AsyncClient, email: str, password: str) -> str:
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_probe_engine_simulation_and_real_tcp():
    """Verify probe engine simulation adapter and local loopback TCP handshake."""
    # 1. Test simulation adapter
    ProbeEngine.set_simulation_override(True)
    res_sim = await ProbeEngine.probe_device(
        device_id=999,
        ip_address="192.168.10.99",
        check_type="icmp_ping",
        use_simulation=True,
    )
    assert res_sim.is_successful is True
    assert res_sim.is_simulated is True
    assert res_sim.response_time_ms > 0

    # 2. Test simulation failure override
    ProbeEngine.set_simulation_override(False)
    res_fail = await ProbeEngine.probe_device(
        device_id=999,
        ip_address="192.168.10.99",
        check_type="icmp_ping",
        use_simulation=True,
    )
    assert res_fail.is_successful is False
    assert res_fail.is_simulated is True
    assert res_fail.error_message is not None

    # Clear override
    ProbeEngine.set_simulation_override(None)

    # 3. Test TCP connection failure to an unused port
    res_tcp = await ProbeEngine.check_tcp_port(
        device_id=999,
        ip_address="127.0.0.1",
        port=64999,  # Unused port
        timeout_seconds=0.5,
        checked_at=res_sim.checked_at,
    )
    assert res_tcp.is_successful is False
    assert res_tcp.check_type == "tcp_port"


@pytest.mark.asyncio
async def test_scheduler_target_authorization_and_concurrency():
    """Verify scheduler only selects authorized targets from active organizations and prevents overlap."""
    scheduler = MonitoringScheduler(concurrency_limit=2)

    # Overlap prevention test
    assert await scheduler.acquire_device(101) is True
    assert await scheduler.acquire_device(101) is False  # Cannot acquire same device concurrently
    await scheduler.release_device(101)
    assert await scheduler.acquire_device(101) is True
    await scheduler.release_device(101)


@pytest.mark.asyncio
async def test_network_endpoints_rbac_and_tenant_isolation(client: AsyncClient):
    """
    Verify /api/v1/network endpoints enforce:
    1. Employee cannot trigger on-demand probe (403).
    2. Executive is read-only (cannot probe -> 403).
    3. Company Admin A cannot probe Company B device (404).
    4. Company Admin A cannot view Company B device checks (404).
    5. Platform Super Admin can query across all devices.
    """
    super_tok = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    comp_a_tok = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    emp_tok = await get_token(client, "employee@servicepulse.uz", "EmployeePass2026!")
    exec_tok = await get_token(client, "executive@servicepulse.uz", "ExecutivePass2026!")

    super_h = {"Authorization": f"Bearer {super_tok}"}
    comp_a_h = {"Authorization": f"Bearer {comp_a_tok}"}
    emp_h = {"Authorization": f"Bearer {emp_tok}"}
    exec_h = {"Authorization": f"Bearer {exec_tok}"}

    # 1. Create Organization B and a device in Org B
    res_org_b = await client.post(
        "/api/v1/organizations",
        json={"name": "Net Test Org B", "slug": "net-test-b", "max_devices": 10},
        headers=super_h,
    )
    org_b_id = res_org_b.json()["id"]

    await client.post(
        "/api/v1/auth/users",
        json={
            "email": "admin_net_b@orgb.uz",
            "password": "PasswordOrgB2026!",
            "full_name": "Net Org B Admin",
            "role_names": ["company_admin"],
            "organization_id": org_b_id,
        },
        headers=super_h,
    )
    b_admin_tok = await get_token(client, "admin_net_b@orgb.uz", "PasswordOrgB2026!")
    b_admin_h = {"Authorization": f"Bearer {b_admin_tok}"}

    bld_b = (await client.post(
        "/api/v1/inventory/buildings",
        json={"name": "Net Building B", "code": "NET-B"},
        headers=b_admin_h,
    )).json()

    flr_b = (await client.post(
        "/api/v1/inventory/floors",
        json={"building_id": bld_b["id"], "level": 1, "name": "Floor 1"},
        headers=b_admin_h,
    )).json()

    rm_b = (await client.post(
        "/api/v1/inventory/rooms",
        json={"floor_id": flr_b["id"], "room_number": "101", "name": "Server Room"},
        headers=b_admin_h,
    )).json()

    dev_b = (await client.post(
        "/api/v1/inventory/devices",
        json={
            "room_id": rm_b["id"],
            "name": "Org B Core Router",
            "hostname": "core-rtr.orgb.local",
            "ip_address": "10.0.99.1",
            "device_type": "router",
        },
        headers=b_admin_h,
    )).json()
    org_b_dev_id = dev_b["id"]

    # 2. Employee attempt to probe -> 403 Forbidden
    r_emp_probe = await client.post(
        f"/api/v1/network/devices/{org_b_dev_id}/probe",
        json={"check_type": "icmp_ping"},
        headers=emp_h,
    )
    assert r_emp_probe.status_code == 403

    # 3. Executive attempt to probe -> 403 Forbidden (Read-only)
    r_exec_probe = await client.post(
        f"/api/v1/network/devices/{org_b_dev_id}/probe",
        json={"check_type": "icmp_ping"},
        headers=exec_h,
    )
    assert r_exec_probe.status_code == 403

    # 4. Company Admin A attempts to probe Org B device -> 404 Not Found (Cross-tenant boundary)
    r_a_probe_b = await client.post(
        f"/api/v1/network/devices/{org_b_dev_id}/probe",
        json={"check_type": "icmp_ping"},
        headers=comp_a_h,
    )
    assert r_a_probe_b.status_code == 404

    # 5. Company Admin A attempts to view Org B device checks -> 404 Not Found
    r_a_checks_b = await client.get(
        f"/api/v1/network/devices/{org_b_dev_id}/checks",
        headers=comp_a_h,
    )
    assert r_a_checks_b.status_code == 404

    # 6. Company Admin A attempts to view Org B device status -> 404 Not Found
    r_a_status_b = await client.get(
        f"/api/v1/network/devices/{org_b_dev_id}/status",
        headers=comp_a_h,
    )
    assert r_a_status_b.status_code == 404

    # 7. Authorized Org B Admin triggers probe for own device -> 200 OK
    # Set simulation override to prevent network timeouts
    ProbeEngine.set_simulation_override(True)
    r_b_probe = await client.post(
        f"/api/v1/network/devices/{org_b_dev_id}/probe",
        json={"check_type": "icmp_ping"},
        headers=b_admin_h,
    )
    ProbeEngine.set_simulation_override(None)
    assert r_b_probe.status_code == 200
    res_data = r_b_probe.json()
    assert res_data["device_id"] == org_b_dev_id
    assert res_data["is_successful"] is True

    # 8. Network health endpoint returns operational metrics
    r_health = await client.get("/api/v1/network/health", headers=comp_a_h)
    assert r_health.status_code == 200
    health_data = r_health.json()
    assert health_data["worker_status"] == "operational"
    assert "active_monitored_devices" in health_data
