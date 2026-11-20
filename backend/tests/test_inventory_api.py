"""
ServicePulse - Inventory Infrastructure API Integration Tests
Author: Muhammadyusuf Usmonov
"""
import pytest
from httpx import AsyncClient

from backend.app.core.config import settings


@pytest.fixture
async def admin_headers(client: AsyncClient):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.FIRST_SUPERUSER_EMAIL, "password": settings.FIRST_SUPERUSER_PASSWORD}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
async def employee_headers(client: AsyncClient):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.FIRST_EMPLOYEE_EMAIL, "password": settings.FIRST_EMPLOYEE_PASSWORD}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_get_inventory_tree(client: AsyncClient, admin_headers):
    """Verify inventory hierarchy tree returns buildings, floors, rooms, devices, and counts."""
    resp = await client.get("/api/v1/inventory/tree", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_buildings"] >= 1
    assert data["total_floors"] >= 1
    assert data["total_rooms"] >= 1
    assert data["total_devices"] >= 6

    main_bld = next(b for b in data["buildings"] if b["code"] == "BLD-MAIN")
    assert main_bld["name"] == "Asosiy Bino"
    assert len(main_bld["floors"]) >= 1
    floor = main_bld["floors"][0]
    assert floor["name"] == "2-qavat"
    room = floor["rooms"][0]
    assert room["room_number"] == "204"
    assert len(room["devices"]) == 6


@pytest.mark.asyncio
async def test_inventory_rbac_protection(client: AsyncClient, employee_headers, admin_headers):
    """Verify employees have read access but cannot create or delete infrastructure."""
    # Employee can read tree
    tree_resp = await client.get("/api/v1/inventory/tree", headers=employee_headers)
    assert tree_resp.status_code == 200

    # Employee cannot create building -> 403
    create_bld = {
        "name": "Yangi Bino",
        "code": "BLD-NEW",
        "address": "Toshkent",
        "description": "Yangi bino"
    }
    resp_bld = await client.post("/api/v1/inventory/buildings", json=create_bld, headers=employee_headers)
    assert resp_bld.status_code == 403

    # Employee cannot create device -> 403
    create_dev = {
        "name": "TEST-DEV-01",
        "hostname": "test-dev.local",
        "ip_address": "192.168.10.99",
        "device_type": "workstation"
    }
    resp_dev = await client.post("/api/v1/inventory/devices", json=create_dev, headers=employee_headers)
    assert resp_dev.status_code == 403


@pytest.mark.asyncio
async def test_device_crud_and_filtering(client: AsyncClient, admin_headers):
    """Verify creating, filtering, updating and deleting a device."""
    # 1. Create device
    new_dev = {
        "name": "CORE-SW-01",
        "hostname": "sw-core-01.local",
        "ip_address": "192.168.10.2",
        "mac_address": "00:11:22:33:44:55",
        "device_type": "switch",
        "operating_system": "Cisco IOS",
        "is_monitored": True
    }
    create_resp = await client.post("/api/v1/inventory/devices", json=new_dev, headers=admin_headers)
    assert create_resp.status_code == 201
    dev_data = create_resp.json()
    dev_id = dev_data["id"]
    assert dev_data["name"] == "CORE-SW-01"

    # 2. Filter by device_type
    filter_resp = await client.get("/api/v1/inventory/devices?device_type=switch", headers=admin_headers)
    assert filter_resp.status_code == 200
    switches = filter_resp.json()
    assert any(d["id"] == dev_id for d in switches)

    # 3. Update device
    update_resp = await client.patch(
        f"/api/v1/inventory/devices/{dev_id}",
        json={"name": "CORE-SW-01-UPDATED", "status": "warning"},
        headers=admin_headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "CORE-SW-01-UPDATED"
    assert update_resp.json()["status"] == "warning"

    # 4. Delete device
    del_resp = await client.delete(f"/api/v1/inventory/devices/{dev_id}", headers=admin_headers)
    assert del_resp.status_code == 204

    # 5. Verify deleted
    get_resp = await client.get(f"/api/v1/inventory/devices/{dev_id}", headers=admin_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_building_delete_safeguard(client: AsyncClient, admin_headers):
    """Verify deleting a building containing active devices is rejected."""
    # Find Asosiy Bino
    tree = (await client.get("/api/v1/inventory/tree", headers=admin_headers)).json()
    main_bld = next(b for b in tree["buildings"] if b["code"] == "BLD-MAIN")

    del_resp = await client.delete(f"/api/v1/inventory/buildings/{main_bld['id']}", headers=admin_headers)
    assert del_resp.status_code == 400
    assert "Cannot delete building containing" in del_resp.json()["detail"]
