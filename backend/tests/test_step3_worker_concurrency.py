"""
ServicePulse - Step 3 Worker Concurrency, Leadership & Restart Tests
Verifies:
1. Singleton worker leadership (WorkerLeaseManager).
2. Secondary worker safely refuses leadership when another is active.
3. Clean shutdown releases the lock.
4. Process crash/disconnect allows immediate recovery by subsequent worker.
5. Device failure counters and active outage intervals survive worker/processor recreation.
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.core.config import settings
from backend.app.db.session import engine
from backend.app.models.inventory import Device
from backend.app.models.monitoring import (
    DeviceMonitoringConfig,
    OutageInterval,
)
from backend.app.models.organization import Organization
from backend.app.schemas.monitoring import ProbeResult
from backend.app.workers.incident_processor import NetworkIncidentProcessor
from backend.app.workers.lease_manager import WorkerLeaseManager
from backend.app.workers.network_worker import NetworkWorker


@pytest.mark.asyncio
async def test_worker_lease_singleton_and_refusal():
    """Verify one worker acquires leadership and secondary worker safely refuses."""
    lock_id = 99991234
    worker1_lease = WorkerLeaseManager(lock_id=lock_id)
    worker2_lease = WorkerLeaseManager(lock_id=lock_id)

    # 1. Worker 1 acquires lease
    assert await worker1_lease.acquire_lease() is True
    assert worker1_lease.is_leader is True

    # 2. Worker 2 attempts to acquire same lease -> refuses leadership
    assert await worker2_lease.acquire_lease() is False
    assert worker2_lease.is_leader is False

    # 3. Worker 1 shuts down and releases lease
    await worker1_lease.release_lease()
    assert worker1_lease.is_leader is False

    # 4. Worker 2 can now acquire leadership
    assert await worker2_lease.acquire_lease() is True
    assert worker2_lease.is_leader is True

    # Clean up
    await worker2_lease.release_lease()


@pytest.mark.asyncio
async def test_worker_start_refuses_leadership_when_already_held():
    """Verify NetworkWorker.start() aborts safely when leadership cannot be obtained."""
    lock_id = 99995678
    external_lease = WorkerLeaseManager(lock_id=lock_id)
    assert await external_lease.acquire_lease() is True

    # Secondary worker instance trying to start with same lock ID
    worker = NetworkWorker(lease_manager=WorkerLeaseManager(lock_id=lock_id))
    started = await worker.start()

    # Worker immediately returns False and refuses to run
    assert started is False
    assert worker.is_running is False

    # Release external lease
    await external_lease.release_lease()


@pytest.mark.asyncio
async def test_postgresql_advisory_lock_session_scope_and_recovery():
    """
    Direct PostgreSQL integration test:
    Verify pg_try_advisory_lock behaves as a singleton across independent connections,
    and closing a connection automatically releases the advisory lock upon crash.
    """
    if engine.dialect.name != "postgresql":
        pytest.skip("Test requires PostgreSQL engine")

    test_pg_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    lock_id = 99998888
    try:
        conn1 = await test_pg_engine.connect()
        try:
            res1 = await conn1.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id})
            assert res1.scalar() is True

            # Second connection attempts same lock -> False
            conn2 = await test_pg_engine.connect()
            try:
                res2 = await conn2.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id})
                assert res2.scalar() is False
            finally:
                await conn2.close()

            # Simulate crash/disconnect of conn1
            await conn1.close()
            conn1 = None

            # Third connection attempts to acquire -> now succeeds
            conn3 = await test_pg_engine.connect()
            try:
                res3 = await conn3.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id})
                assert res3.scalar() is True
                await conn3.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id})
            finally:
                await conn3.close()
        finally:
            if conn1 is not None and not conn1.closed:
                await conn1.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id})
                await conn1.close()
    finally:
        await test_pg_engine.dispose()


@pytest.mark.asyncio
async def test_device_state_and_outages_persist_across_worker_recreation(test_db: AsyncSession):
    """
    Verify that device consecutive_failures and active OutageIntervals
    survive complete destruction and recreation of workers and incident processors.
    """
    db = test_db
    now = datetime.now(timezone.utc)

    org = Organization(name="Persistence Org", slug="pers-org", max_devices=5)
    db.add(org)
    await db.flush()

    dev = Device(
        organization_id=org.id,
        name="Router-Core-Alpha",
        hostname="rtr-alpha.lan",
        ip_address="10.200.1.1",
        device_type="router",
        status="online",
        consecutive_failures=0,
        is_monitored=True,
        is_sample_data=False,
    )
    db.add(dev)
    await db.flush()

    cfg = DeviceMonitoringConfig(
        device_id=dev.id,
        is_enabled=True,
        is_authorized=True,
        ping_enabled=True,
        consecutive_failure_threshold=3,
        simulation_mode=False,
    )
    db.add(cfg)
    await db.commit()

    dev_id = dev.id

    # -------------------------------------------------------------------------
    # Cycle 1: First Worker Instance records 2 probe failures
    # -------------------------------------------------------------------------
    processor_v1 = NetworkIncidentProcessor()
    fail_res_1 = ProbeResult(
        device_id=dev_id,
        target_ip="10.200.1.1",
        check_type="icmp_ping",
        is_successful=False,
        response_time_ms=0.0,
        packet_loss_percent=100.0,
        error_message="Host unreachable",
        checked_at=now,
    )
    await processor_v1.process_probe_result(fail_res_1, dev, cfg, db)
    await processor_v1.process_probe_result(fail_res_1, dev, cfg, db)
    await db.commit()

    assert dev.consecutive_failures == 2
    assert dev.status == "warning"

    # -------------------------------------------------------------------------
    # Simulating Process Crash / Restart:
    # Completely destroy processor_v1 and worker references.
    # -------------------------------------------------------------------------
    del processor_v1

    # Re-query device in fresh context
    dev_reloaded = (await db.execute(select(Device).where(Device.id == dev_id))).scalar_one()
    assert dev_reloaded.consecutive_failures == 2
    assert dev_reloaded.status == "warning"

    # -------------------------------------------------------------------------
    # Cycle 2: New Worker Instance (Processor v2) runs 3rd probe failure
    # Reaching threshold (3) -> transitions to offline and starts OutageInterval
    # -------------------------------------------------------------------------
    processor_v2 = NetworkIncidentProcessor()
    await processor_v2.process_probe_result(fail_res_1, dev_reloaded, cfg, db)
    await db.commit()

    assert dev_reloaded.consecutive_failures == 3
    assert dev_reloaded.status == "offline"

    # Verify active outage interval was created in DB
    outage_q = select(OutageInterval).where(
        OutageInterval.device_id == dev_id,
        OutageInterval.ended_at.is_(None)
    )
    outage = (await db.execute(outage_q)).scalar_one_or_none()
    assert outage is not None
    assert outage.ended_at is None
    outage_id = outage.id
    outage_start_time = outage.started_at

    # -------------------------------------------------------------------------
    # Simulating Second Process Crash / Restart during ongoing outage:
    # Destroy processor_v2
    # -------------------------------------------------------------------------
    del processor_v2

    # -------------------------------------------------------------------------
    # Cycle 3: Third Worker Instance (Processor v3) processes successful recovery probe
    # -------------------------------------------------------------------------
    dev_reloaded_2 = (await db.execute(select(Device).where(Device.id == dev_id))).scalar_one()
    assert dev_reloaded_2.status == "offline"

    processor_v3 = NetworkIncidentProcessor()
    succ_res = ProbeResult(
        device_id=dev_id,
        target_ip="10.200.1.1",
        check_type="icmp_ping",
        is_successful=True,
        response_time_ms=1.5,
        packet_loss_percent=0.0,
        checked_at=now,
    )
    await processor_v3.process_probe_result(succ_res, dev_reloaded_2, cfg, db)
    await db.commit()

    # Verify device status recovered to online and failure counter reset
    assert dev_reloaded_2.status == "online"
    assert dev_reloaded_2.consecutive_failures == 0

    # Verify original active outage interval was successfully closed with duration
    closed_outage = (await db.execute(select(OutageInterval).where(OutageInterval.id == outage_id))).scalar_one()
    assert closed_outage.ended_at is not None
    assert closed_outage.started_at == outage_start_time
    assert closed_outage.duration_seconds >= 0.0
