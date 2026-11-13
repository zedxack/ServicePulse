"""
ServicePulse - Step 3 Incident Lifecycle, Deduplication & Automated Recovery Tests
Verifies consecutive failure thresholds, device state transitions, verified OutageIntervals,
incident deduplication, and automated recovery resolution.
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.incident import Incident
from backend.app.models.inventory import Device
from backend.app.models.monitoring import (
    DeviceMonitoringConfig,
    OutageInterval,
)
from backend.app.models.organization import Organization
from backend.app.schemas.monitoring import ProbeResult
from backend.app.workers.incident_processor import NetworkIncidentProcessor


@pytest.mark.asyncio
async def test_consecutive_failure_threshold_and_state_transition(test_db: AsyncSession):
    """
    Verify:
    1. First failure sets status to warning.
    2. Reaching threshold (3) sets status to offline, creates OutageInterval, and creates Incident.
    3. Duplicate failures increment occurrence count without creating duplicate incidents.
    4. Successful probe closes OutageInterval, transitions device to online, and auto-resolves incident.
    """
    db = test_db

    # Create test organization
    org = Organization(name="Incident Lifecycle Test Org", slug="inc-life-org", max_devices=5)
    db.add(org)
    await db.flush()

    # Create test device
    dev = Device(
        organization_id=org.id,
        name="Lifecycle Switch",
        hostname="sw-life.local",
        ip_address="10.200.1.1",
        device_type="switch",
        status="online",
        consecutive_failures=0,
        is_monitored=True,
        is_sample_data=True,
    )
    db.add(dev)
    await db.flush()

    cfg = DeviceMonitoringConfig(
        device_id=dev.id,
        is_enabled=True,
        is_authorized=True,
        ping_enabled=True,
        consecutive_failure_threshold=3,
        simulation_mode=True,
    )
    db.add(cfg)
    await db.commit()

    dev_id = dev.id
    cfg_id = cfg.id

    # -------------------------------------------------------------------------
    # 1. First probe failure: status -> warning
    # -------------------------------------------------------------------------
    now1 = datetime.now(timezone.utc)
    res_fail1 = ProbeResult(
        device_id=dev_id,
        target_ip="10.200.1.1",
        check_type="icmp_ping",
        is_successful=False,
        response_time_ms=0.0,
        packet_loss_percent=100.0,
        error_message="Host unreachable",
        is_simulated=True,
        checked_at=now1,
    )
    d = await db.get(Device, dev_id)
    c = await db.get(DeviceMonitoringConfig, cfg_id)
    inc1 = await NetworkIncidentProcessor.process_probe_result(res_fail1, d, c, db)
    await db.commit()
    assert d.status == "warning"
    assert d.consecutive_failures == 1
    assert inc1 is None  # Threshold not reached yet

    # -------------------------------------------------------------------------
    # 2. Second probe failure: status stays warning
    # -------------------------------------------------------------------------
    now2 = datetime.now(timezone.utc)
    res_fail2 = ProbeResult(
        device_id=dev_id,
        target_ip="10.200.1.1",
        check_type="icmp_ping",
        is_successful=False,
        response_time_ms=0.0,
        packet_loss_percent=100.0,
        error_message="Host unreachable",
        is_simulated=True,
        checked_at=now2,
    )
    d = await db.get(Device, dev_id)
    c = await db.get(DeviceMonitoringConfig, cfg_id)
    inc2 = await NetworkIncidentProcessor.process_probe_result(res_fail2, d, c, db)
    await db.commit()
    assert d.status == "warning"
    assert d.consecutive_failures == 2
    assert inc2 is None

    # -------------------------------------------------------------------------
    # 3. Third probe failure (threshold reached): status -> offline, incident created
    # -------------------------------------------------------------------------
    now3 = datetime.now(timezone.utc)
    res_fail3 = ProbeResult(
        device_id=dev_id,
        target_ip="10.200.1.1",
        check_type="icmp_ping",
        is_successful=False,
        response_time_ms=0.0,
        packet_loss_percent=100.0,
        error_message="Host unreachable",
        is_simulated=True,
        checked_at=now3,
    )
    d = await db.get(Device, dev_id)
    c = await db.get(DeviceMonitoringConfig, cfg_id)
    inc3 = await NetworkIncidentProcessor.process_probe_result(res_fail3, d, c, db)
    await db.commit()
    assert d.status == "offline"
    assert d.consecutive_failures == 3
    assert inc3 is not None
    assert inc3.status == "open"
    assert inc3.occurrence_count == 1
    created_inc_id = inc3.id

    # Verify OutageInterval was recorded
    outage_q = select(OutageInterval).where(OutageInterval.device_id == dev_id, OutageInterval.ended_at.is_(None))
    outage = (await db.execute(outage_q)).scalar_one_or_none()
    assert outage is not None
    assert outage.incident_id == created_inc_id

    # -------------------------------------------------------------------------
    # 4. Fourth probe failure (deduplication while offline): occurrence_count -> 2
    # -------------------------------------------------------------------------
    now4 = datetime.now(timezone.utc)
    res_fail4 = ProbeResult(
        device_id=dev_id,
        target_ip="10.200.1.1",
        check_type="icmp_ping",
        is_successful=False,
        response_time_ms=0.0,
        packet_loss_percent=100.0,
        error_message="Host unreachable",
        is_simulated=True,
        checked_at=now4,
    )
    d = await db.get(Device, dev_id)
    c = await db.get(DeviceMonitoringConfig, cfg_id)
    inc4 = await NetworkIncidentProcessor.process_probe_result(res_fail4, d, c, db)
    await db.commit()
    assert inc4 is not None
    assert inc4.id == created_inc_id  # Reused same active incident
    assert inc4.occurrence_count == 2
    assert d.status == "offline"

    # -------------------------------------------------------------------------
    # 5. Probe Success (Recovery): status -> online, outage closed, incident resolved
    # -------------------------------------------------------------------------
    now5 = datetime.now(timezone.utc)
    res_success = ProbeResult(
        device_id=dev_id,
        target_ip="10.200.1.1",
        check_type="icmp_ping",
        is_successful=True,
        response_time_ms=3.2,
        packet_loss_percent=0.0,
        error_message=None,
        is_simulated=True,
        checked_at=now5,
    )
    d = await db.get(Device, dev_id)
    c = await db.get(DeviceMonitoringConfig, cfg_id)
    await NetworkIncidentProcessor.process_probe_result(res_success, d, c, db)
    await db.commit()
    assert d.status == "online"
    assert d.consecutive_failures == 0

    # OutageInterval must now have ended_at and duration_seconds
    outage_q = select(OutageInterval).where(OutageInterval.device_id == dev_id)
    closed_outage = (await db.execute(outage_q)).scalar_one_or_none()
    assert closed_outage is not None
    assert closed_outage.ended_at is not None
    assert closed_outage.duration_seconds is not None
    assert closed_outage.duration_seconds >= 0.0

    # Active incident must now be resolved
    inc = await db.get(Incident, created_inc_id)
    assert inc.status == "resolved"
    assert inc.active_dedup_key is None  # Deduplication key cleared upon resolution
