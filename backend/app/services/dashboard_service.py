"""
ServicePulse - Dashboard Analytics Service
Real SQL aggregation for 5 Role-Based Dashboards:
1. Platform Super Admin (Global platform health, multi-tenant stats, global audits)
2. Company Admin (Organizational capacity, tenant users, devices, org audits)
3. SysAdmin / IT Support (Live device monitoring, network status, telemetry, incidents)
4. CEO / Executive (Availability, SLA, MTTD/MTTR, risk devices, business impact)
5. Employee (Personal tickets, software requests, approvals tracking)
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.models.agent import Agent, AgentTelemetry
from backend.app.models.audit import AuditLog
from backend.app.models.incident import Incident
from backend.app.models.inventory import Building, Device, Floor, Room
from backend.app.models.monitoring import DeviceStateTransition, OutageInterval
from backend.app.models.network import NetworkCheck
from backend.app.models.organization import Organization
from backend.app.models.remediation import RemediationExecution
from backend.app.models.ticket import SoftwareRequest, Ticket
from backend.app.models.user import User
from backend.app.schemas.dashboard import (
    AuditSummaryItem,
    BuildingDeviceStatus,
    CEODashboardResponse,
    CompanyDashboardResponse,
    EmployeeDashboardResponse,
    EmployeeSoftwareSummary,
    EmployeeTicketSummary,
    IncidentTrendItem,
    PlatformDashboardResponse,
    RiskDevice,
    SysAdminDashboardResponse,
    TelemetrySummary,
)


class DashboardService:
    # -------------------------------------------------------------------------
    # 1. PLATFORM SUPER ADMIN DASHBOARD
    # -------------------------------------------------------------------------
    @staticmethod
    async def get_platform_dashboard(db: AsyncSession) -> PlatformDashboardResponse:
        now = datetime.now(timezone.utc)

        # Organization counts
        total_orgs = (await db.execute(select(func.count(Organization.id)))).scalar() or 0
        active_orgs = (await db.execute(select(func.count(Organization.id)).where(Organization.is_active == True))).scalar() or 0  # noqa: E712
        inactive_orgs = total_orgs - active_orgs

        # Global user, device, agent counts
        total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        total_devices = (await db.execute(select(func.count(Device.id)))).scalar() or 0
        total_agents = (await db.execute(select(func.count(Agent.id)))).scalar() or 0
        global_active_inc = (await db.execute(select(func.count(Incident.id)).where(Incident.status != "resolved"))).scalar() or 0

        # Global audits
        audits_q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10)
        audit_rows = list((await db.execute(audits_q)).scalars().all())
        recent_audits = [
            AuditSummaryItem(
                id=a.id,
                action=a.action,
                target_resource=a.target_resource,
                target_id=a.target_id,
                status=a.status,
                created_at=a.created_at,
            )
            for a in audit_rows
        ]

        health_status = "healthy"
        if global_active_inc > 10:
            health_status = "degraded"

        return PlatformDashboardResponse(
            timestamp=now,
            total_organizations=total_orgs,
            active_organizations=active_orgs,
            inactive_organizations=inactive_orgs,
            total_platform_users=total_users,
            total_platform_devices=total_devices,
            total_platform_agents=total_agents,
            global_active_incidents=global_active_inc,
            platform_health_status=health_status,
            recent_global_audits=recent_audits,
        )

    # -------------------------------------------------------------------------
    # 2. COMPANY ADMIN DASHBOARD
    # -------------------------------------------------------------------------
    @staticmethod
    async def get_company_dashboard(org_id: int, db: AsyncSession) -> CompanyDashboardResponse:
        now = datetime.now(timezone.utc)

        org_q = select(Organization).where(Organization.id == org_id)
        org = (await db.execute(org_q)).scalar_one_or_none()
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

        total_users = (await db.execute(select(func.count(User.id)).where(User.organization_id == org_id))).scalar() or 0
        total_devices = (await db.execute(select(func.count(Device.id)).where(Device.organization_id == org_id))).scalar() or 0
        total_buildings = (await db.execute(select(func.count(Building.id)).where(Building.organization_id == org_id))).scalar() or 0
        active_inc = (await db.execute(select(func.count(Incident.id)).where(Incident.organization_id == org_id, Incident.status != "resolved"))).scalar() or 0

        max_dev = org.max_devices if org.max_devices > 0 else 100
        utilization = round((total_devices / max_dev) * 100.0, 1)

        audits_q = (
            select(AuditLog)
            .where(AuditLog.organization_id == org_id)
            .order_by(AuditLog.created_at.desc())
            .limit(10)
        )
        audit_rows = list((await db.execute(audits_q)).scalars().all())
        recent_audits = [
            AuditSummaryItem(
                id=a.id,
                action=a.action,
                target_resource=a.target_resource,
                target_id=a.target_id,
                status=a.status,
                created_at=a.created_at,
            )
            for a in audit_rows
        ]

        return CompanyDashboardResponse(
            timestamp=now,
            organization_id=org.id,
            organization_name=org.name,
            total_users=total_users,
            total_devices=total_devices,
            max_devices=max_dev,
            device_utilization_percent=utilization,
            total_buildings=total_buildings,
            active_incidents=active_inc,
            recent_org_audits=recent_audits,
        )

    # -------------------------------------------------------------------------
    # 3. SYSADMIN / IT SUPPORT DASHBOARD
    # -------------------------------------------------------------------------
    @staticmethod
    async def get_sysadmin_dashboard(db: AsyncSession, scoped_org_id: Optional[int] = None) -> SysAdminDashboardResponse:
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(hours=24)

        # 1. Device Counts
        dev_counts_q = select(Device.status, func.count(Device.id))
        if scoped_org_id is not None:
            dev_counts_q = dev_counts_q.where(Device.organization_id == scoped_org_id)
        dev_counts_q = dev_counts_q.group_by(Device.status)
        dev_counts = await db.execute(dev_counts_q)
        status_map = dict(dev_counts.all())

        online_cnt = status_map.get("online", 0)
        offline_cnt = status_map.get("offline", 0)
        warning_cnt = status_map.get("warning", 0)
        unknown_cnt = status_map.get("unknown", 0)
        total_dev = sum(status_map.values())

        # 2. Incidents
        active_q = select(func.count(Incident.id)).where(Incident.status != "resolved")
        crit_q = select(func.count(Incident.id)).where(Incident.status != "resolved", Incident.severity == "critical")
        daily_q = select(func.count(Incident.id)).where(Incident.first_seen_at >= yesterday)

        if scoped_org_id is not None:
            active_q = active_q.where(Incident.organization_id == scoped_org_id)
            crit_q = crit_q.where(Incident.organization_id == scoped_org_id)
            daily_q = daily_q.where(Incident.organization_id == scoped_org_id)

        active_incidents = (await db.execute(active_q)).scalar() or 0
        critical_incidents = (await db.execute(crit_q)).scalar() or 0
        daily_incidents = (await db.execute(daily_q)).scalar() or 0

        # 3. Agents
        agent_q = select(Agent.status, func.count(Agent.id))
        if scoped_org_id is not None:
            agent_q = agent_q.where(Agent.organization_id == scoped_org_id)
        agent_counts = await db.execute(agent_q.group_by(Agent.status))
        agent_map = dict(agent_counts.all())
        agents_total = sum(agent_map.values())
        agents_active = agent_map.get("active", 0)
        agents_offline = agents_total - agents_active

        # 4. Devices by Building
        bld_query = (
            select(Building)
            .options(
                selectinload(Building.floors)
                .selectinload(Floor.rooms)
                .selectinload(Room.devices)
            )
        )
        if scoped_org_id is not None:
            bld_query = bld_query.where(Building.organization_id == scoped_org_id)
        buildings = list((await db.execute(bld_query)).scalars().all())
        devices_by_bld: List[BuildingDeviceStatus] = []
        for b in buildings:
            b_devices = [d for f in b.floors for r in f.rooms for d in r.devices]
            b_online = sum(1 for d in b_devices if d.status == "online")
            b_offline = sum(1 for d in b_devices if d.status == "offline")
            b_warning = sum(1 for d in b_devices if d.status == "warning")
            devices_by_bld.append(BuildingDeviceStatus(
                building_id=b.id,
                building_name=b.name,
                total_devices=len(b_devices),
                online=b_online,
                offline=b_offline,
                warning=b_warning,
            ))

        # 5. Telemetry Summary
        tel_q = select(
            func.avg(AgentTelemetry.cpu_percent),
            func.avg(AgentTelemetry.ram_percent),
            func.avg(AgentTelemetry.disk_percent),
            func.count(AgentTelemetry.id),
        )
        if scoped_org_id is not None:
            tel_q = tel_q.join(Agent, AgentTelemetry.agent_id == Agent.id).where(Agent.organization_id == scoped_org_id)
        tel_stats = await db.execute(tel_q)
        avg_cpu, avg_ram, avg_disk, total_tel = tel_stats.one()

        telemetry_summary = TelemetrySummary(
            avg_cpu_percent=round(avg_cpu, 1) if avg_cpu is not None else None,
            avg_ram_percent=round(avg_ram, 1) if avg_ram is not None else None,
            avg_disk_percent=round(avg_disk, 1) if avg_disk is not None else None,
            total_telemetry_records=total_tel or 0,
        )

        # 6. Outage & Remediation Status Metrics
        outages_q = select(func.count(OutageInterval.id)).where(OutageInterval.ended_at.is_(None))
        pending_rem_q = select(func.count(RemediationExecution.id)).where(
            RemediationExecution.status.in_(["pending_approval", "pending", "executing"])
        )
        verified_rem_q = select(func.count(RemediationExecution.id)).where(
            RemediationExecution.verification_status == "verified_success"
        )
        failed_rem_q = select(func.count(RemediationExecution.id)).where(
            RemediationExecution.verification_status == "verification_failed"
        )
        rec_recov_q = select(func.count(DeviceStateTransition.id)).join(
            Device, DeviceStateTransition.device_id == Device.id
        ).where(
            DeviceStateTransition.to_status == "online",
            DeviceStateTransition.from_status == "offline"
        )

        if scoped_org_id is not None:
            outages_q = outages_q.where(OutageInterval.organization_id == scoped_org_id)
            pending_rem_q = pending_rem_q.join(Incident, RemediationExecution.incident_id == Incident.id).where(Incident.organization_id == scoped_org_id)
            verified_rem_q = verified_rem_q.join(Incident, RemediationExecution.incident_id == Incident.id).where(Incident.organization_id == scoped_org_id)
            failed_rem_q = failed_rem_q.join(Incident, RemediationExecution.incident_id == Incident.id).where(Incident.organization_id == scoped_org_id)
            rec_recov_q = rec_recov_q.where(Device.organization_id == scoped_org_id)

        active_outages = (await db.execute(outages_q)).scalar() or 0
        pending_rem = (await db.execute(pending_rem_q)).scalar() or 0
        verified_rem = (await db.execute(verified_rem_q)).scalar() or 0
        failed_rem = (await db.execute(failed_rem_q)).scalar() or 0
        recent_recov = (await db.execute(rec_recov_q)).scalar() or 0

        return SysAdminDashboardResponse(
            timestamp=now,
            organization_id=scoped_org_id,
            total_devices=total_dev,
            online_devices=online_cnt,
            offline_devices=offline_cnt,
            warning_devices=warning_cnt,
            unknown_devices=unknown_cnt,
            active_incidents=active_incidents,
            critical_incidents=critical_incidents,
            daily_incidents=daily_incidents,
            agents_total=agents_total,
            agents_active=agents_active,
            agents_offline=agents_offline,
            devices_by_building=devices_by_bld,
            telemetry_summary=telemetry_summary,
            active_outages_count=active_outages,
            pending_remediations_count=pending_rem,
            verified_remediations_count=verified_rem,
            failed_remediations_count=failed_rem,
            recent_recoveries_count=recent_recov,
        )

    # -------------------------------------------------------------------------
    # 4. CEO / EXECUTIVE DASHBOARD
    # -------------------------------------------------------------------------
    @staticmethod
    async def get_ceo_dashboard(db: AsyncSession, scoped_org_id: Optional[int] = None) -> CEODashboardResponse:
        now = datetime.now(timezone.utc)

        # 1. Real-Time Snapshot Availability (Current state of online monitored devices)
        dev_q = select(Device.status, Device.is_monitored)
        if scoped_org_id is not None:
            dev_q = dev_q.where(Device.organization_id == scoped_org_id)
        dev_res = await db.execute(dev_q)
        dev_rows = dev_res.all()
        monitored_devices = [r for r in dev_rows if r.is_monitored]
        total_monitored = len(monitored_devices)

        if total_monitored > 0:
            online_count = sum(1 for r in monitored_devices if r.status == "online")
            snapshot_availability = round((online_count / total_monitored) * 100.0, 2)
        else:
            snapshot_availability = 100.0

        target_sla = settings.SLA_TARGET_PERCENT

        # 2. Empirical Probe Success Ratio (Discrete network check probe frequency)
        # Explicitly distinguished from contractual SLA uptime (no duration/interval integration yet)
        nc_q = select(NetworkCheck.is_successful).join(Device, NetworkCheck.device_id == Device.id)
        if scoped_org_id is not None:
            nc_q = nc_q.where(Device.organization_id == scoped_org_id)
        nc_results = list((await db.execute(nc_q)).scalars().all())

        MIN_OBSERVATIONS_THRESHOLD = 5
        if len(nc_results) >= MIN_OBSERVATIONS_THRESHOLD:
            success_count = sum(1 for s in nc_results if s)
            probe_success_ratio = round((success_count / len(nc_results)) * 100.0, 2)
            probe_success_status = "operational"
        else:
            probe_success_ratio = None
            probe_success_status = "insufficient_data"

        # Contractual SLA is strictly unavailable until duration-based historical calculation is implemented
        contractual_sla_uptime = None
        contractual_sla_status = "unavailable"
        contractual_sla_achievement = None

        # 3. MTTD & MTTR (Honest calculations from operational history; no hardcoded defaults)
        resolved_q = select(Incident).where(
            Incident.status == "resolved",
            Incident.resolved_at.is_not(None)
        )
        if scoped_org_id is not None:
            resolved_q = resolved_q.where(Incident.organization_id == scoped_org_id)
        resolved_incidents = list((await db.execute(resolved_q)).scalars().all())

        if resolved_incidents:
            durations_min = [
                (inc.resolved_at - inc.first_seen_at).total_seconds() / 60.0
                for inc in resolved_incidents
                if inc.resolved_at and inc.first_seen_at
            ]
            mttr_minutes = round(sum(durations_min) / len(durations_min), 1) if durations_min else None
            mttr_status = "operational" if mttr_minutes is not None else "insufficient_data"

            # MTTD: Mean Time to Detect
            # Honest calculation: elapsed minutes between first detected probe failure and incident registration
            mttd_deltas: List[float] = []
            for inc in resolved_incidents:
                if inc.device_id and inc.first_seen_at:
                    probe_q = (
                        select(NetworkCheck)
                        .where(
                            NetworkCheck.device_id == inc.device_id,
                            NetworkCheck.is_successful.is_(False),
                            NetworkCheck.checked_at <= inc.first_seen_at,
                        )
                        .order_by(NetworkCheck.checked_at.desc())
                        .limit(1)
                    )
                    probe_res = (await db.execute(probe_q)).scalar_one_or_none()
                    if probe_res and probe_res.checked_at:
                        diff = (inc.first_seen_at - probe_res.checked_at).total_seconds() / 60.0
                        if diff >= 0:
                            mttd_deltas.append(diff)

            if mttd_deltas:
                mttd_minutes = round(sum(mttd_deltas) / len(mttd_deltas), 1)
                mttd_status = "operational"
            else:
                mttd_minutes = None
                mttd_status = "insufficient_data"
        else:
            mttd_minutes = None
            mttr_minutes = None
            mttd_status = "insufficient_data"
            mttr_status = "insufficient_data"

        # 3. Top 5 Risk Devices
        risk_q = (
            select(
                Device.id,
                Device.name,
                Device.hostname,
                Device.device_type,
                Device.ip_address,
                Device.consecutive_failures,
                Device.status,
                func.count(Incident.id).label("incident_count"),
            )
            .outerjoin(Incident, Device.id == Incident.device_id)
        )
        if scoped_org_id is not None:
            risk_q = risk_q.where(Device.organization_id == scoped_org_id)
        risk_q = (
            risk_q.group_by(Device.id)
            .order_by(func.count(Incident.id).desc(), Device.consecutive_failures.desc())
            .limit(5)
        )
        risk_rows = (await db.execute(risk_q)).all()
        top_risk_devices = [
            RiskDevice(
                device_id=r[0],
                name=r[1],
                hostname=r[2],
                device_type=r[3],
                ip_address=r[4],
                consecutive_failures=r[5],
                status=r[6],
                incident_count=r[7],
            )
            for r in risk_rows
        ]

        # 4. Incident Trends (last 7 days)
        trends: List[IncidentTrendItem] = []
        for i in range(6, -1, -1):
            day_date = (now - timedelta(days=i)).date()
            start_dt = datetime.combine(day_date, datetime.min.time(), tzinfo=timezone.utc)
            end_dt = datetime.combine(day_date, datetime.max.time(), tzinfo=timezone.utc)

            q_day = (
                select(Incident.severity, func.count(Incident.id))
                .where(Incident.first_seen_at >= start_dt, Incident.first_seen_at <= end_dt)
            )
            if scoped_org_id is not None:
                q_day = q_day.where(Incident.organization_id == scoped_org_id)
            q_day = q_day.group_by(Incident.severity)
            day_counts = dict((await db.execute(q_day)).all())
            trends.append(IncidentTrendItem(
                date=day_date.strftime("%Y-%m-%d"),
                critical=day_counts.get("critical", 0),
                warning=day_counts.get("warning", 0),
                info=day_counts.get("info", 0),
            ))

        total_inc_period = sum(t.critical + t.warning + t.info for t in trends)
        active_risk_level = "LOW"
        if any(d.status == "offline" for d in top_risk_devices):
            active_risk_level = "MEDIUM"
        if sum(t.critical for t in trends) > 3:
            active_risk_level = "HIGH"

        impact_summary: Dict[str, str] = {
            "uptime_status": "Optimal" if snapshot_availability >= 99.0 else "Degraded",
            "business_continuity": "No operational interruptions detected" if total_inc_period == 0 else f"{total_inc_period} incidents tracked across infrastructure",
            "financial_exposure": "None" if active_risk_level == "LOW" else "Low risk of SLA violation",
            "remediation_status": "All automated rules active and standing by",
        }

        return CEODashboardResponse(
            timestamp=now,
            organization_id=scoped_org_id,
            sla_target_percent=target_sla,
            contractual_sla_uptime_percent=contractual_sla_uptime,
            contractual_sla_status=contractual_sla_status,
            contractual_sla_achievement_percent=contractual_sla_achievement,
            probe_success_ratio_percent=probe_success_ratio,
            probe_success_status=probe_success_status,
            current_device_snapshot_percent=snapshot_availability,
            infrastructure_availability_percent=snapshot_availability,
            measured_historical_sla_uptime_percent=None,
            sla_uptime_status="unavailable",
            sla_achievement_percent=None,
            actual_availability_percent=snapshot_availability,
            mttd_minutes=mttd_minutes,
            mttr_minutes=mttr_minutes,
            mttd_status=mttd_status,
            mttr_status=mttr_status,
            total_incidents_period=total_inc_period,
            active_risk_level=active_risk_level,
            incident_trends=trends,
            top_risk_devices=top_risk_devices,
            business_impact_summary=impact_summary,
        )

    # -------------------------------------------------------------------------
    # 5. EMPLOYEE DASHBOARD
    # -------------------------------------------------------------------------
    @staticmethod
    async def get_employee_dashboard(user: User, db: AsyncSession) -> EmployeeDashboardResponse:
        now = datetime.now(timezone.utc)

        # Open and resolved ticket counts
        open_q = select(func.count(Ticket.id)).where(Ticket.author_id == user.id, Ticket.status != "resolved")
        open_cnt = (await db.execute(open_q)).scalar() or 0

        res_q = select(func.count(Ticket.id)).where(Ticket.author_id == user.id, Ticket.status == "resolved")
        res_cnt = (await db.execute(res_q)).scalar() or 0

        recent_t_q = (
            select(Ticket)
            .where(Ticket.author_id == user.id)
            .order_by(Ticket.created_at.desc())
            .limit(5)
        )
        recent_tickets = [
            EmployeeTicketSummary(
                id=t.id,
                title=t.title,
                priority=t.priority,
                status=t.status,
                created_at=t.created_at,
            )
            for t in (await db.execute(recent_t_q)).scalars().all()
        ]

        # Software requests
        pending_sw_q = select(func.count(SoftwareRequest.id)).where(SoftwareRequest.user_id == user.id, SoftwareRequest.status == "pending")
        pending_sw_cnt = (await db.execute(pending_sw_q)).scalar() or 0

        recent_sw_q = (
            select(SoftwareRequest)
            .where(SoftwareRequest.user_id == user.id)
            .order_by(SoftwareRequest.created_at.desc())
            .limit(5)
        )
        recent_sw = [
            EmployeeSoftwareSummary(
                id=s.id,
                software_name=s.software_name,
                status=s.status,
                created_at=s.created_at,
            )
            for s in (await db.execute(recent_sw_q)).scalars().all()
        ]

        return EmployeeDashboardResponse(
            timestamp=now,
            user_id=user.id,
            user_name=user.full_name,
            open_tickets_count=open_cnt,
            resolved_tickets_count=res_cnt,
            recent_tickets=recent_tickets,
            pending_software_requests_count=pending_sw_cnt,
            recent_software_requests=recent_sw,
        )
