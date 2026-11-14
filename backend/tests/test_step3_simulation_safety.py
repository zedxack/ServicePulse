"""
ServicePulse - Step 3 Simulation Safety & Production Isolation Tests
Verifies:
1. Production environment rejects global WORKER_SIMULATION_MODE=true.
2. Real devices (is_sample_data=False) never enter simulation mode.
3. Test simulation overrides are reliably isolated and reset.
4. Simulated data is excluded from production uptime calculations.
5. Simulated remediations cannot count as verified production success.
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import Settings
from backend.app.models.incident import Incident
from backend.app.models.inventory import Device
from backend.app.models.monitoring import (
    DeviceMonitoringConfig,
)
from backend.app.models.network import NetworkCheck
from backend.app.models.organization import Organization
from backend.app.models.remediation import RemediationExecution, RemediationRule
from backend.app.services.remediation_verification import RemediationVerification
from backend.app.services.uptime_service import UptimeService
from backend.app.workers.network_worker import NetworkWorker
from backend.app.workers.probe_engine import ProbeEngine


def test_production_environment_rejects_worker_simulation_mode():
    """Verify production environment strictly rejects global simulation_mode=true."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            WORKER_SIMULATION_MODE=True,
        )
    assert "WORKER_SIMULATION_MODE cannot be enabled in production environment" in str(exc_info.value)


@pytest.mark.asyncio
async def test_real_devices_never_enter_simulation(test_db: AsyncSession):
    """
    Verify real devices (is_sample_data=False) always execute real probes
    even if config.simulation_mode is mistakenly toggled or global simulation is requested.
    """
    db = test_db
    org = Organization(name="Real Device Org", slug="real-dev-org", max_devices=5)
    db.add(org)
    await db.flush()

    real_dev = Device(
        organization_id=org.id,
        name="Real Production Firewall",
        hostname="fw01.prod.lan",
        ip_address="192.168.10.1",  # Typical LAN IP
        device_type="firewall",
        status="online",
        is_monitored=True,
        is_sample_data=False,  # Explicitly NOT sample data
    )
    db.add(real_dev)
    await db.flush()

    # Even if simulation_mode is True in config:
    cfg = DeviceMonitoringConfig(
        device_id=real_dev.id,
        is_enabled=True,
        is_authorized=True,
        ping_enabled=False,
        tcp_ports="64991",
        simulation_mode=True,  # Mistakenly set to True
    )
    db.add(cfg)
    await db.commit()

    worker = NetworkWorker()
    # Execute single probe for real device with test session
    probe_res = await worker.run_single_probe(real_dev, cfg, db=db)
    await db.commit()

    assert probe_res is not None
    # Real probe was executed: is_simulated MUST be False
    assert probe_res.is_simulated is False

    # Query recorded NetworkCheck
    from sqlalchemy import select
    res = await db.execute(select(NetworkCheck).where(NetworkCheck.device_id == real_dev.id))
    check = res.scalar_one_or_none()
    assert check is not None
    assert check.check_type == "tcp_port"


def test_probe_engine_simulation_override_isolation():
    """Verify test overrides are strictly isolated and reset."""
    ProbeEngine.reset_simulation_override()
    assert ProbeEngine._simulation_override is None

    # Context manager sets and automatically resets
    with ProbeEngine.temporary_simulation_override(True):
        assert ProbeEngine._simulation_override is True

    # After exit, override is back to None
    assert ProbeEngine._simulation_override is None


@pytest.mark.asyncio
async def test_simulated_devices_excluded_from_production_uptime(test_db: AsyncSession):
    """
    Verify simulated sample devices do not count toward production SLA.
    When only_production=True, sample devices are excluded.
    """
    db = test_db
    now = datetime.now(timezone.utc)

    org = Organization(name="Mixed Device Org", slug="mixed-org", max_devices=5)
    db.add(org)
    await db.flush()

    # 1. Sample device
    sample_dev = Device(
        organization_id=org.id,
        name="Sample Workstation",
        hostname="sample-ws.lab",
        ip_address="10.0.0.99",
        device_type="workstation",
        status="online",
        is_monitored=True,
        is_sample_data=True,
    )
    # 2. Real production device
    real_dev = Device(
        organization_id=org.id,
        name="Production Database Host",
        hostname="db01.prod.lan",
        ip_address="10.0.1.5",
        device_type="server",
        status="online",
        is_monitored=True,
        is_sample_data=False,
    )
    db.add(sample_dev)
    db.add(real_dev)
    await db.commit()

    # Record 15 checks for real device
    for i in range(15):
        db.add(NetworkCheck(
            device_id=real_dev.id,
            check_type="icmp_ping",
            is_successful=True,
            response_time_ms=1.2,
            packet_loss_percent=0.0,
            checked_at=now - timedelta(days=1, hours=i),
        ))
    await db.commit()

    # Production SLA query (only_production=True):
    # Only the 1 real device should be counted; sample_dev must be excluded.
    prod_summary = await UptimeService.get_organization_downtime_summary(
        org_id=org.id,
        window_days=30,
        only_production=True,
        db=db,
    )
    assert prod_summary["total_monitored_devices"] == 1
    assert prod_summary["uptime_status"] == "operational"


@pytest.mark.asyncio
async def test_simulated_remediation_cannot_count_as_production_success(test_db: AsyncSession):
    """
    Verify that simulated remediations set verification_status='simulated_verification'
    and explicitly log that they are NOT counted as production success.
    """
    db = test_db
    org = Organization(name="Remediation Safety Org", slug="rem-safety", max_devices=5)
    db.add(org)
    await db.flush()

    rule = RemediationRule(
        organization_id=org.id,
        name="Simulation Restart Rule",
        trigger_condition="device_offline",
        action_name="restart_service",
        action_parameters='{"service_name": "ServicePulseAgent"}',
        is_active=True,
        requires_approval=False,
    )
    db.add(rule)
    await db.flush()

    # Create incident for execution
    inc = Incident(
        organization_id=org.id,
        title="Simulation Test Incident",
        description="Trigger for simulation verification",
        severity="critical",
        status="investigating",
        fingerprint="test_sim_inc_001",
    )
    db.add(inc)
    await db.flush()

    # Create a simulated execution
    execution = RemediationExecution(
        rule_id=rule.id,
        incident_id=inc.id,
        status="executing",
        verification_status="pending",
        is_simulation=True,
    )
    db.add(execution)
    await db.commit()

    # Verify execution outcome
    verified, log_msg = await RemediationVerification.verify_execution(execution.id, db)
    assert verified is True
    assert "Not counted as production success" in log_msg

    await db.refresh(execution)
    assert execution.verification_status == "simulated_verification"
    assert "SIMULATED" in execution.verification_log
