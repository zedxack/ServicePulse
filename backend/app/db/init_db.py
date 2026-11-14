"""
ServicePulse - Database Seeding & Initialization Module
Populates Multi-Tenant Organizations, 6 RBAC Roles, fine-grained permissions,
administrative accounts, and realistic demonstration infrastructure.
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.security import hash_password
from backend.app.db.base import Base
from backend.app.db.session import AsyncSessionLocal, engine
from backend.app.models import (
    AuditLog,
    Building,
    Device,
    DeviceMonitoringConfig,
    Floor,
    NetworkCheck,
    Organization,
    Permission,
    RemediationRule,
    Role,
    Room,
    User,
)


async def init_db(db: AsyncSession) -> None:
    """Seed initial multi-tenant system data if not already present."""
    logger.info("Checking and seeding database initial records...")

    # 1. Demonstration Organization
    result = await db.execute(select(Organization).where(Organization.slug == "demo-org"))
    demo_org = result.scalar_one_or_none()
    if not demo_org:
        demo_org = Organization(
            name="TATU AT-Servis Lab",
            slug="demo-org",
            domain="tatu.uz",
            is_active=True,
            max_devices=100,
        )
        db.add(demo_org)
        await db.flush()
        logger.info("Created demonstration organization: %s (slug: %s)", demo_org.name, demo_org.slug)

    # 2. Granular Permissions
    permissions_data = [
        ("platform:manage", "Platform Management", "Full administrative control across all organizations"),
        ("org:manage", "Organization Management", "Manage company settings, limits, and organizational data"),
        ("users:manage", "User Management", "Create, modify, and deactivate users within organization"),
        ("inventory:read", "Read Inventory", "View buildings, floors, rooms and devices"),
        ("inventory:write", "Write Inventory", "Create, edit, and decommission inventory infrastructure"),
        ("incident:read", "Read Incidents", "View active and historical incidents"),
        ("incident:write", "Manage Incidents", "Assign, acknowledge, and comment on incidents"),
        ("incident:resolve", "Resolve Incidents", "Mark incidents as resolved and clear deduplication keys"),
        ("remediation:read", "Read Remediation", "View automated remediation rules and executions"),
        ("remediation:execute", "Execute Remediation", "Trigger or approve automated remediation actions"),
        ("agent:read", "Read Agents", "View enrolled agents and telemetry"),
        ("agent:manage", "Manage Agents", "Enroll, rotate keys, and decommission agents"),
        ("ticket:read_all", "Read All Tickets", "View all support tickets across the organization"),
        ("ticket:manage", "Manage Tickets", "Assign and resolve support tickets"),
        ("ticket:create", "Create Tickets", "Submit personal support tickets"),
        ("software:request", "Request Software", "Submit software installation requests"),
        ("software:approve", "Approve Software", "Approve or reject software installation requests"),
        ("audit:read", "Read Audit Logs", "Inspect security and operational audit trails"),
        ("dashboard:platform", "Platform Dashboard", "Access global platform-wide intelligence dashboard"),
        ("dashboard:company", "Company Dashboard", "Access organization-level management dashboard"),
        ("dashboard:sysadmin", "SysAdmin Dashboard", "Access live infrastructure and technical operations dashboard"),
        ("dashboard:executive", "Executive Dashboard", "Access SLA, MTTD, MTTR, and availability dashboard"),
        ("dashboard:employee", "Employee Dashboard", "Access self-service support tickets and requests dashboard"),
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

    # 3. Six RBAC Roles
    roles_data = [
        (
            "platform_super_admin",
            "Platform Super Administrator",
            list(permission_map.values()),
        ),
        (
            "company_admin",
            "Company / Organization Administrator",
            [
                p for c, p in permission_map.items()
                if not c.startswith("platform:")
            ],
        ),
        (
            "it_admin",
            "Lead IT Infrastructure Administrator",
            [
                p for c, p in permission_map.items()
                if c in [
                    "inventory:read", "inventory:write",
                    "incident:read", "incident:write", "incident:resolve",
                    "remediation:read", "remediation:execute", "remediation:approve",
                    "agent:read", "agent:manage",
                    "ticket:read_all", "ticket:manage", "ticket:create",
                    "software:approve", "software:request",
                    "audit:read", "dashboard:sysadmin", "dashboard:employee"
                ]
            ],
        ),
        (
            "support",
            "IT Support Engineer",
            [
                p for c, p in permission_map.items()
                if c in [
                    "inventory:read", "inventory:write",
                    "incident:read", "incident:write",
                    "agent:read",
                    "ticket:read_all", "ticket:manage", "ticket:create",
                    "software:request",
                    "dashboard:sysadmin", "dashboard:employee"
                ]
            ],
        ),
        (
            "executive",
            "CEO / Executive Officer",
            [
                p for c, p in permission_map.items()
                if c in [
                    "inventory:read", "incident:read",
                    "dashboard:executive", "dashboard:employee", "audit:read"
                ]
            ],
        ),
        (
            "employee",
            "Organization Staff Member",
            [
                p for c, p in permission_map.items()
                if c in [
                    "inventory:read", "ticket:create", "software:request", "dashboard:employee"
                ]
            ],
        ),
        # Legacy backward-compatibility alias for initial tests
        (
            "admin",
            "Legacy Admin Alias",
            list(permission_map.values()),
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
        else:
            role.permissions = perms
            db.add(role)
        role_map[role_name] = role

    # 4. Default Seed Accounts Across Roles
    users_data = [
        (
            settings.FIRST_SUPERUSER_EMAIL,
            settings.FIRST_SUPERUSER_PASSWORD,
            "System Administrator",
            ["platform_super_admin", "admin"],
            True,
            demo_org.id,
        ),
        (
            "company_admin@servicepulse.uz",
            "CompanyAdminPass2026!",
            "TATU Lab Administrator",
            ["company_admin"],
            False,
            demo_org.id,
        ),
        (
            settings.FIRST_SUPPORT_EMAIL,
            settings.FIRST_SUPPORT_PASSWORD,
            "Support Engineer",
            ["it_admin", "support"],
            False,
            demo_org.id,
        ),
        (
            "executive@servicepulse.uz",
            "ExecutivePass2026!",
            "University Dean / Executive",
            ["executive"],
            False,
            demo_org.id,
        ),
        (
            settings.FIRST_EMPLOYEE_EMAIL,
            settings.FIRST_EMPLOYEE_PASSWORD,
            "Muhammadyusuf Usmonov",
            ["employee"],
            False,
            demo_org.id,
        ),
    ]

    for email, plain_pw, full_name, user_roles_list, is_super, org_id in users_data:
        result = await db.execute(select(User).options(selectinload(User.roles)).where(User.email == email))
        user = result.scalar_one_or_none()
        assigned_roles = [role_map[r] for r in user_roles_list if r in role_map]
        if not user:
            user = User(
                email=email,
                hashed_password=hash_password(plain_pw),
                full_name=full_name,
                is_active=True,
                is_superuser=is_super,
                organization_id=org_id,
                roles=assigned_roles,
            )
            db.add(user)
            await db.flush()
            logger.info("Created user: %s (Roles: %s, Org: %s)", email, ", ".join(user_roles_list), org_id)
        else:
            if user.organization_id is None:
                user.organization_id = org_id
            user.roles = assigned_roles
            db.add(user)

    # Ensure buildings and devices have organization_id set
    await db.execute(
        sa_update(Building).where(Building.organization_id.is_(None)).values(organization_id=demo_org.id)
    )
    await db.execute(
        sa_update(Device).where(Device.organization_id.is_(None)).values(organization_id=demo_org.id)
    )

    # 5. Realistic Demonstration Infrastructure (Asosiy Bino -> 2-qavat -> 204-Laboratoriya)
    result = await db.execute(select(Building).where(Building.code == "BLD-MAIN"))
    main_bld = result.scalar_one_or_none()
    if not main_bld:
        main_bld = Building(
            organization_id=demo_org.id,
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

        # Demo Devices
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
                organization_id=demo_org.id,
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
        logger.info("Created demonstration infrastructure for %s with 6 demo devices.", demo_org.name)

        # Seed baseline historical network check observations for realistic SLA computation
        demo_devs = (await db.execute(select(Device).where(Device.organization_id == demo_org.id))).scalars().all()
        for d in demo_devs:
            for offset_m in [120, 90, 60, 45, 30, 15, 5]:
                check_time = datetime.now(timezone.utc) - timedelta(minutes=offset_m)
                nc = NetworkCheck(
                    device_id=d.id,
                    check_type="icmp_ping",
                    is_successful=True,
                    response_time_ms=2.5,
                    packet_loss_percent=0.0,
                    checked_at=check_time,
                )
                db.add(nc)
            # Seed monitoring configuration
            cfg_q = select(DeviceMonitoringConfig).where(DeviceMonitoringConfig.device_id == d.id)
            existing_cfg = (await db.execute(cfg_q)).scalar_one_or_none()
            if not existing_cfg:
                tcp_p = "80,443"
                if d.device_type == "router":
                    tcp_p = "80,443,8291"
                elif d.device_type == "ip_camera":
                    tcp_p = "554,80"
                db.add(DeviceMonitoringConfig(
                    device_id=d.id,
                    is_enabled=True,
                    is_authorized=True,
                    ping_enabled=True,
                    tcp_ports=tcp_p,
                    check_interval_seconds=30,
                    timeout_seconds=3.0,
                    consecutive_failure_threshold=3,
                    simulation_mode=True,
                ))
        await db.flush()

    # 6. Automated Remediation Rules
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
            "recheck_network_endpoint",
            '{"timeout_seconds": 3.0}',
            False,
        ),
    ]

    for name, desc, trig, ttype, action, params, req_app in remediation_rules:
        result = await db.execute(select(RemediationRule).where(RemediationRule.name == name))
        rule = result.scalar_one_or_none()
        if not rule:
            rule = RemediationRule(
                organization_id=demo_org.id,
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
        else:
            rule.action_name = action
            rule.action_parameters = params
    await db.flush()

    # 7. Initial Audit Record
    audit = AuditLog(
        organization_id=demo_org.id,
        user_id=None,
        action="system_seed_init",
        target_resource="database",
        target_id="0",
        status="success",
        details="System seed completed with multi-tenant structure, 6 RBAC roles, and demo assets.",
    )
    db.add(audit)
    await db.commit()
    logger.info("Multi-tenant database seeding completed successfully.")


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await init_db(session)


if __name__ == "__main__":
    asyncio.run(main())
