"""
ServicePulse - Stage 6: RMM Fleet Automation Integration Tests
Tests:
1. Subnet Auto-Discovery Scanner (POST /api/v1/inventory/discover-subnet)
2. Bulk Discovered Nodes Import (POST /api/v1/inventory/import-discovered)
3. 1-Click Agent Bootstrap Generator (GET /api/v1/agents/bootstrap-config)
4. Allowlisted Remote Actions (POST /api/v1/inventory/devices/{id}/remote-action)
5. Live Process & Service Snapshot (GET /api/v1/inventory/devices/{id}/process-snapshot)
6. Tenant boundary protection on fleet automation
Author: Muhammadyusuf Usmonov
"""
import pytest
from httpx import AsyncClient


async def get_token(client: AsyncClient, email: str, password: str) -> str:
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_subnet_auto_discovery_scanner(client: AsyncClient):
    token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Unauthenticated request rejected
    unauth = await client.post("/api/v1/inventory/discover-subnet", json={"subnet_cidr": "192.168.10.0/24"})
    assert unauth.status_code == 401

    # 2. Invalid CIDR format rejected
    bad_res = await client.post(
        "/api/v1/inventory/discover-subnet",
        json={"subnet_cidr": "invalid-cidr-mask"},
        headers=headers,
    )
    assert bad_res.status_code == 400
    assert "Invalid subnet CIDR" in bad_res.json()["detail"]

    # 3. Successful Fast Scan
    res_fast = await client.post(
        "/api/v1/inventory/discover-subnet",
        json={"subnet_cidr": "192.168.10.0/24", "scan_mode": "fast"},
        headers=headers,
    )
    assert res_fast.status_code == 200, f"Fast scan failed: {res_fast.text}"
    data_fast = res_fast.json()

    assert data_fast["subnet_cidr"] == "192.168.10.0/24"
    assert data_fast["total_probed"] > 0
    assert data_fast["discovered_count"] >= 3
    assert len(data_fast["candidates"]) >= 3

    # Verify candidate contract
    cand = data_fast["candidates"][0]
    assert "ip_address" in cand
    assert "hostname" in cand
    assert "mac_address" in cand
    assert "detected_device_type" in cand
    assert "open_ports" in cand
    assert "response_time_ms" in cand
    assert "already_registered" in cand

    # 4. Deep Scan includes additional edge ports and nodes
    res_deep = await client.post(
        "/api/v1/inventory/discover-subnet",
        json={"subnet_cidr": "10.50.0.0/24", "scan_mode": "deep"},
        headers=headers,
    )
    assert res_deep.status_code == 200
    data_deep = res_deep.json()
    assert data_deep["discovered_count"] >= len(data_fast["candidates"])


@pytest.mark.asyncio
async def test_bulk_discovered_nodes_import(client: AsyncClient):
    token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    headers = {"Authorization": f"Bearer {token}"}

    import_payload = {
        "devices": [
            {
                "ip_address": "192.168.10.101",
                "hostname": "auto-ws-finance-01",
                "mac_address": "00:11:22:33:44:55",
                "device_type": "workstation",
                "operating_system": "Windows 11 Enterprise",
            },
            {
                "ip_address": "192.168.10.102",
                "hostname": "auto-sw-edge-02",
                "mac_address": "00:11:22:33:44:66",
                "device_type": "switch",
                "operating_system": "Cisco IOS-XE",
            },
        ]
    }

    # 1. First import should register both nodes
    res = await client.post("/api/v1/inventory/import-discovered", json=import_payload, headers=headers)
    assert res.status_code == 201, f"Import failed: {res.text}"
    data = res.json()
    assert data["imported_count"] == 2
    assert data["skipped_count"] == 0
    assert len(data["created_device_ids"]) == 2

    # 2. Second import with identical IPs should skip them
    res_dup = await client.post("/api/v1/inventory/import-discovered", json=import_payload, headers=headers)
    assert res_dup.status_code == 201
    data_dup = res_dup.json()
    assert data_dup["imported_count"] == 0
    assert data_dup["skipped_count"] == 2

    # 3. Subnet discovery on the same subnet now flags these IPs as already_registered=True
    res_scan = await client.post(
        "/api/v1/inventory/discover-subnet",
        json={"subnet_cidr": "192.168.10.0/24", "scan_mode": "fast"},
        headers=headers,
    )
    assert res_scan.status_code == 200
    scan_data = res_scan.json()
    imported_candidates = [c for c in scan_data["candidates"] if c["ip_address"] in ["192.168.10.101", "192.168.10.102"]]
    for c in imported_candidates:
        assert c["already_registered"] is True


@pytest.mark.asyncio
async def test_agent_bootstrap_config_generator(client: AsyncClient):
    token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    headers = {"Authorization": f"Bearer {token}"}

    # Test both /api/v1/agents/bootstrap-config and /api/v1/agent/bootstrap-config
    for endpoint in ["/api/v1/agents/bootstrap-config", "/api/v1/agent/bootstrap-config"]:
        res = await client.get(endpoint, headers=headers)
        assert res.status_code == 200, f"Endpoint {endpoint} failed: {res.text}"
        data = res.json()

        assert "powershell_command" in data
        assert "linux_bash_command" in data
        assert "server_url" in data
        assert "organization_id" in data
        assert "organization_name" in data
        assert "enrollment_secret_masked" in data
        assert len(data["manual_steps"]) >= 2

        # Verify PowerShell one-liner script signature
        ps_cmd = data["powershell_command"]
        assert "Install-ServicePulseAgent" in ps_cmd
        assert "Set-ExecutionPolicy Bypass" in ps_cmd
        assert "-EnrollmentSecret" in ps_cmd

        # Verify Linux bash one-liner script signature
        sh_cmd = data["linux_bash_command"]
        assert "curl -fsSL" in sh_cmd
        assert "--enrollment-secret" in sh_cmd


@pytest.mark.asyncio
async def test_remote_actions_and_process_snapshot(client: AsyncClient):
    token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch an existing device
    devices_res = await client.get("/api/v1/inventory/devices", headers=headers)
    assert devices_res.status_code == 200
    devices = devices_res.json()
    assert len(devices) > 0
    test_device = devices[0]
    dev_id = test_device["id"]

    # 2. Get process & system service snapshot
    snapshot_res = await client.get(f"/api/v1/inventory/devices/{dev_id}/process-snapshot", headers=headers)
    assert snapshot_res.status_code == 200, f"Snapshot failed: {snapshot_res.text}"
    snap = snapshot_res.json()

    assert snap["device_id"] == dev_id
    assert len(snap["top_processes"]) >= 4
    assert len(snap["system_services"]) >= 4

    # Verify process model
    proc = snap["top_processes"][0]
    assert "pid" in proc
    assert "name" in proc
    assert "cpu_percent" in proc
    assert "ram_mb" in proc

    # Verify service model
    svc = snap["system_services"][0]
    assert "name" in svc
    assert "display_name" in svc
    assert svc["status"] in ["RUNNING", "STOPPED"]

    # 3. Allowlisted Remote Action: restart_service
    restart_res = await client.post(
        f"/api/v1/inventory/devices/{dev_id}/remote-action",
        json={"action": "restart_service", "parameters": {"service_name": "Spooler"}},
        headers=headers,
    )
    assert restart_res.status_code == 200, f"Restart service failed: {restart_res.text}"
    restart_data = restart_res.json()
    assert restart_data["action"] == "restart_service"
    assert restart_data["status"] == "executed"
    assert restart_data["verification_status"] == "verified_success"
    assert "Spooler" in restart_data["execution_result"]

    # 4. Allowlisted Remote Action: kill_process
    kill_res = await client.post(
        f"/api/v1/inventory/devices/{dev_id}/remote-action",
        json={"action": "kill_process", "parameters": {"pid": 5420, "process_name": "spoolsv.exe"}},
        headers=headers,
    )
    assert kill_res.status_code == 200
    kill_data = kill_res.json()
    assert kill_data["action"] == "kill_process"
    assert "5420" in kill_data["execution_result"]

    # 5. Prohibited / Non-allowlisted Action rejected with 400
    illegal_res = await client.post(
        f"/api/v1/inventory/devices/{dev_id}/remote-action",
        json={"action": "format_disk", "parameters": {"target": "C:"}},
        headers=headers,
    )
    assert illegal_res.status_code == 400
    assert "not in allowlisted" in illegal_res.json()["detail"]


@pytest.mark.asyncio
async def test_tenant_boundary_on_remote_action(client: AsyncClient):
    # Login as Company Admin of Org 1
    comp_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    comp_headers = {"Authorization": f"Bearer {comp_token}"}

    # Attempt remote action on non-existent or other org device ID
    non_existent_res = await client.post(
        "/api/v1/inventory/devices/99999/remote-action",
        json={"action": "flush_dns"},
        headers=comp_headers,
    )
    assert non_existent_res.status_code == 404
