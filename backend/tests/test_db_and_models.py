"""
ServicePulse - Database Models & Hierarchy Verification Tests
Author: Muhammadyusuf Usmonov
"""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    Building,
    Device,
    Incident,
    RemediationRule,
    Role,
    User,
)


@pytest.mark.asyncio
async def test_seeded_users_and_roles(test_db: AsyncSession):
    """Verify seeded administrator, support and employee users and roles."""
    result = await test_db.execute(select(User).where(User.email == "admin@servicepulse.uz"))
    admin_user = result.scalar_one_or_none()
    assert admin_user is not None
    assert admin_user.is_superuser is True
    assert any(r.name == "admin" for r in admin_user.roles)

    result = await test_db.execute(select(Role))
    roles = result.scalars().all()
    role_names = {r.name for r in roles}
    assert "admin" in role_names
    assert "support" in role_names
    assert "employee" in role_names


@pytest.mark.asyncio
async def test_demonstration_infrastructure_hierarchy(test_db: AsyncSession):
    """
    Verify demonstration infrastructure:
    Asosiy Bino -> 2-qavat -> 204-Laboratoriya -> 6 demo devices
    """
    # 1. Building
    result = await test_db.execute(select(Building).where(Building.code == "BLD-MAIN"))
    building = result.scalar_one_or_none()
    assert building is not None
    assert building.name == "Asosiy Bino"
    assert building.is_sample_data is True
    assert len(building.floors) == 1

    # 2. Floor
    floor = building.floors[0]
    assert floor.level == 2
    assert floor.name == "2-qavat"
    assert len(floor.rooms) == 1

    # 3. Room
    room = floor.rooms[0]
    assert room.room_number == "204"
    assert room.name == "204-Laboratoriya"
    assert len(room.devices) == 6

    # 4. Devices
    device_names = {d.name for d in room.devices}
    expected_devices = {
        "SRV-MAIN-01",
        "RTR-MIKROTIK-CORE",
        "LAB2-PC01",
        "LAB2-PC02",
        "CAM-KIRISH-01",
        "CAM-LAB204-01",
    }
    assert device_names == expected_devices

    # Verify device types
    srv = next(d for d in room.devices if d.name == "SRV-MAIN-01")
    assert srv.device_type == "server"
    assert srv.ip_address == "192.168.10.10"

    rtr = next(d for d in room.devices if d.name == "RTR-MIKROTIK-CORE")
    assert rtr.device_type == "router"
    assert rtr.ip_address == "192.168.10.1"


@pytest.mark.asyncio
async def test_create_device_and_incident(test_db: AsyncSession):
    """Verify creating a device and associated incident record."""
    device = Device(
        name="TEST-SWITCH-01",
        hostname="sw-test-01.local",
        ip_address="192.168.10.5",
        device_type="switch",
        status="online",
        is_monitored=True
    )
    test_db.add(device)
    await test_db.flush()
    assert device.id is not None

    incident = Incident(
        device_id=device.id,
        fingerprint="fp-test-switch-port1",
        title="Switch Uplink Flapping",
        description="Port 1 state transitioned down/up 5 times in 1 minute",
        severity="warning",
        status="open"
    )
    test_db.add(incident)
    await test_db.flush()
    assert incident.id is not None
    assert incident.occurrence_count == 1
    assert incident.device.name == "TEST-SWITCH-01"


@pytest.mark.asyncio
async def test_remediation_rules_seeded(test_db: AsyncSession):
    """Verify seeded remediation rules."""
    result = await test_db.execute(select(RemediationRule))
    rules = result.scalars().all()
    assert len(rules) >= 3
    rule_actions = {r.action_name for r in rules}
    assert "restart_service" in rule_actions
    assert "check_network" in rule_actions
