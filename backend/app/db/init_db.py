"""
ServicePulse - Database Seeding & Initialization Module
Populates default roles, administrative accounts, realistic demonstration
infrastructure (Asosiy Bino -> 2-qavat -> 204-Laboratoriya), and initial rules.
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.core.security import hash_password
from backend.app.db.base import Base
from backend.app.db.session import AsyncSessionLocal, engine
from backend.app.models import (
    AuditLog,
    Building,
    Device,
    Floor,
    Permission,
    RemediationRule,
    Role,
    Room,
    User,
)


async def init_db(db: AsyncSession) -> None:
    """Seed initial system data if not already present."""
    logger.info("Checking and seeding database initial records...")

    # 1. Standard Permissions
    permissions_data = [
        ("inventory:read", "Read Inventory", "View buildings, floors, rooms and devices"),
        ("inventory:write", "Write Inventory", "Create and edit inventory infrastructure"),
        ("incident:read", "Read Incidents", "View system incidents and events"),
        ("incident:write", "Manage Incidents", "Assign, comment, and update incidents"),
        ("remediation:read", "Read Remediation", "View automated remediation rules and executions"),
        ("remediation:execute", "Execute Remediation", "Trigger or approve automated remediation actions"),
        ("agent:read", "Read Agents", "View enrolled agents and telemetry"),
        ("agent:manage", "Manage Agents", "Enroll, rotate keys, and decommission agents"),
        ("audit:read", "Read Audit Logs", "Inspect security and administrative audit trails"),
        ("settings:manage", "Manage Settings", "Configure system-wide settings and monitoring thresholds"),
    ]

    permission_map = {}
    for code, name, desc in permissions_data:
        result = await db.execute(select(Permission).where(Permission.code == code))
        perm = result.scalar_one_or_none()
        if not perm:
            perm = Permission(code=code, name=name, description=desc)
            db.add(perm)
            await db.flush()
        permission_map[code] = perm

    # 2. Standard Roles
    roles_data = [
        ("admin", "System Administrator", list(permission_map.values())),
        (
            "support",
            "IT Support Engineer",
            [
                p for c, p in permission_map.items()
                if c in ["inventory:read", "inventory:write", "incident:read", "incident:write", "remediation:read", "agent:read"]
            ],
        ),
        (
            "employee",
            "Organization Employee",
            [p for c, p in permission_map.items() if c in ["inventory:read", "incident:read"]],
        ),
    ]

    role_map = {}
    for role_name, desc, perms in roles_data:
        result = await db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()
        if not role:
            role = Role(name=role_name, description=desc, permissions=perms)
            db.add(role)
            await db.flush()
        role_map[role_name] = role

    # 3. Default Administrative & Demo Users
    users_data = [
        ("admin@servicepulse.uz", "AdminPass2026!", "System Administrator", ["admin"], True),
        ("support@servicepulse.uz", "SupportPass2026!", "Support Engineer", ["support"], False),
        ("employee@servicepulse.uz", "EmployeePass2026!", "Muhammadyusuf Usmonov", ["employee"], False),
    ]

    for email, plain_pw, full_name, user_roles_list, is_super in users_data:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            assigned_roles = [role_map[r] for r in user_roles_list if r in role_map]
            user = User(
                email=email,
                hashed_password=hash_password(plain_pw),
                full_name=full_name,
                is_active=True,
                is_superuser=is_super,
                roles=assigned_roles,
            )
            db.add(user)
            await db.flush()
            logger.info("Created user: %s (Role: %s)", email, ", ".join(user_roles_list))

    # 4. Realistic Demonstration Infrastructure (Asosiy Bino -> 2-qavat -> 204-Laboratoriya)
    result = await db.execute(select(Building).where(Building.code == "BLD-MAIN"))
    main_bld = result.scalar_one_or_none()
    if not main_bld:
        main_bld = Building(
            name="Asosiy Bino",
            code="BLD-MAIN",
            address="Toshkent shahri, Universitet ko'chasi 7",
            description="Toshkent axborot texnologiyalari markazi asosiy o'quv va ma'muriy binosi",
            is_sample_data=True,
        )
        db.add(main_bld)
        await db.flush()

        # Floor 2
        floor_2 = Floor(
            building_id=main_bld.id,
            level=2,
            name="2-qavat",
            description="Axborot texnologiyalari va dasturiy injiniring kafedrasi qavati",
            is_sample_data=True,
        )
        db.add(floor_2)
        await db.flush()

        # Room 204
        room_204 = Room(
            floor_id=floor_2.id,
            room_number="204",
            name="204-Laboratoriya",
            description="AT-Servis amaliy tadqiqotlar va kompyuter tarmoqlari laboratoriyasi",
            is_sample_data=True,
        )
        db.add(room_204)
        await db.flush()

        # Devices (Sample Infrastructure)
        demo_devices = [
            ("SRV-MAIN-01", "srv-main-01.servicepulse.local", "192.168.10.10", "00:1A:2B:3C:4D:01", "server", "Windows Server 2022"),
            ("RTR-MIKROTIK-CORE", "gw-core.servicepulse.local", "192.168.10.1", "00:1A:2B:3C:4D:02", "router", "RouterOS v7"),
            ("LAB2-PC01", "lab2-pc01.servicepulse.local", "192.168.10.21", "00:1A:2B:3C:4D:21", "workstation", "Windows 11 Pro"),
            ("LAB2-PC02", "lab2-pc02.servicepulse.local", "192.168.10.22", "00:1A:2B:3C:4D:22", "workstation", "Windows 11 Pro"),
            ("CAM-KIRISH-01", "cam-kirish-01.servicepulse.local", "192.168.10.50", "00:1A:2B:3C:4D:50", "ip_camera", "Embedded Linux RTSP"),
            ("CAM-LAB204-01", "cam-lab204-01.servicepulse.local", "192.168.10.51", "00:1A:2B:3C:4D:51", "ip_camera", "Embedded Linux RTSP"),
        ]

        for name, hostname, ip, mac, dtype, os_name in demo_devices:
            dev = Device(
                room_id=room_204.id,
                name=name,
                hostname=hostname,
                ip_address=ip,
                mac_address=mac,
                device_type=dtype,
                operating_system=os_name,
                status="online",
                is_monitored=True,
                is_sample_data=True,
                last_seen=datetime.now(timezone.utc),
                last_heartbeat=datetime.now(timezone.utc),
            )
            db.add(dev)
        await db.flush()
        logger.info("Created demonstration infrastructure: Asosiy Bino -> 2-qavat -> 204-Laboratoriya with 6 demo devices.")

    # 5. Standard Automated Remediation Rules
    remediation_rules = [
        (
            "Restart ServicePulse Agent on High Latency / Service Failure",
            "Auto-restarts ServicePulse Agent if telemetry fails or service is unresponsive",
            "agent_offline",
            "workstation",
            "restart_service",
            '{"service_name": "ServicePulseAgent"}',
            False,
        ),
        (
            "Restart Windows Print Spooler on Error",
            "Restarts Spooler service when print subsystem reports critical failure",
            "service_spooler_failed",
            "workstation",
            "restart_service",
            '{"service_name": "Spooler"}',
            False,
        ),
        (
            "Recheck Network Gateway on Connectivity Loss",
            "Triggers diagnostic ARP and gateway ping when device loses LAN connection",
            "ping_timeout",
            None,
            "check_network",
            '{"target": "192.168.10.1"}',
            False,
        ),
    ]

    for name, desc, trig, ttype, action, params, req_app in remediation_rules:
        result = await db.execute(select(RemediationRule).where(RemediationRule.name == name))
        rule = result.scalar_one_or_none()
        if not rule:
            rule = RemediationRule(
                name=name,
                description=desc,
                trigger_condition=trig,
                target_device_type=ttype,
                action_name=action,
                action_parameters=params,
                requires_approval=req_app,
                is_active=True,
                max_retries=2,
                cooldown_seconds=300,
            )
            db.add(rule)
    await db.flush()

    # 6. Initial Audit Log Entry
    audit = AuditLog(
        user_id=None,
        action="system_seed_init",
        target_resource="database",
        target_id="0",
        status="success",
        details="Initial system seed executed: roles, users, demo infrastructure, remediation rules created.",
    )
    db.add(audit)
    await db.commit()
    logger.info("Database seeding completed successfully.")


async def main() -> None:
    """Standalone seeding execution entrypoint."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await init_db(session)


if __name__ == "__main__":
    asyncio.run(main())
