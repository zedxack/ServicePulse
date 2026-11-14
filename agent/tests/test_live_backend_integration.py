"""
ServicePulse Live Backend Integration Verification Test
Tests live end-to-end integration against running Docker PostgreSQL backend.
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
import datetime
import tempfile
import time
from pathlib import Path

import asyncpg
import httpx
import pytest
from servicepulse.api_client import ApiClient
from servicepulse.authentication import CredentialStore
from servicepulse.collectors.defender import DefenderCollector
from servicepulse.collectors.network import NetworkCollector
from servicepulse.collectors.system import SystemCollector
from servicepulse.collectors.windows_activation import WindowsActivationCollector
from servicepulse.config import AgentConfig
from servicepulse.queue.storage import QueueStorage
from servicepulse.queue.sync import QueueSyncWorker


def is_backend_online() -> bool:
    """Check if the local Docker backend is reachable."""
    try:
        r = httpx.get("http://localhost:8000/health", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


@pytest.mark.asyncio
async def test_live_docker_backend_telemetry_and_queue_flow():
    """Verify live enrollment, real telemetry collection, SQLite offline queueing, and PostgreSQL verification."""
    if not is_backend_online():
        pytest.skip("Docker backend is not running at http://localhost:8000")

    # Connect to PostgreSQL in Docker
    db_conn = await asyncpg.connect("postgresql://postgres:postgres_password_2026@localhost:5432/servicepulse")

    tmp_dir = Path(tempfile.mkdtemp(prefix="sp_live_test_"))
    creds_path = tmp_dir / "credentials.dat"
    queue_path = tmp_dir / "queue.db"

    config = AgentConfig(
        server_url="http://localhost:8000",
        data_dir=str(tmp_dir),
        simulation_mode=False
    )
    cred_store = CredentialStore(creds_path)
    api_client = ApiClient(config, cred_store)

    enrolled_agent_id = None

    try:
        # 1. Real Enrollment
        enroll_secret = "servicepulse-agent-enrollment-secret-2026"
        creds = api_client.enroll(
            enrollment_secret=enroll_secret,
            hostname="AUDIT-WORKSTATION-WIN11",
            os_name="Windows 11 Pro 64-bit (Audit)",
            ip_address=NetworkCollector.get_primary_ip()
        )
        assert creds.agent_uuid is not None
        cred_store.save_credentials(creds)

        # Verify in PostgreSQL
        row = await db_conn.fetchrow(
            "SELECT id, agent_uuid, hostname, status, created_at FROM agents WHERE agent_uuid = $1",
            creds.agent_uuid
        )
        assert row is not None
        enrolled_agent_id = row["id"]
        assert row["status"] == "active"

        # 2. Collect Real Host Telemetry
        sys_metrics = SystemCollector.collect_all()
        act_info = WindowsActivationCollector.collect()
        def_info = DefenderCollector.collect()

        assert sys_metrics.cpu.cpu_percent >= 0.0
        assert sys_metrics.ram.ram_total_mb > 0.0
        assert sys_metrics.disk.disk_total_gb > 0.0

        # 3. Transmit Real Telemetry
        idemp_key_1 = f"tx_live_test_{int(time.time())}_1"
        telemetry_1 = {
            "cpu_percent": sys_metrics.cpu.cpu_percent,
            "ram_percent": sys_metrics.ram.ram_percent,
            "ram_used_mb": sys_metrics.ram.ram_used_mb,
            "ram_total_mb": sys_metrics.ram.ram_total_mb,
            "disk_percent": sys_metrics.disk.disk_percent,
            "disk_used_gb": sys_metrics.disk.disk_used_gb,
            "disk_total_gb": sys_metrics.disk.disk_total_gb,
            "windows_activation_status": act_info.status,
            "windows_defender_status": def_info.status,
            "idempotency_key": idemp_key_1,
            "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        resp = api_client.submit_telemetry(telemetry_1)
        assert resp.get("status") == "recorded"
        assert resp.get("is_duplicate") is False

        # 4. Verify Telemetry & Heartbeat in PostgreSQL
        t_row = await db_conn.fetchrow(
            "SELECT id, agent_id, cpu_percent, ram_percent, disk_percent, windows_activation_status, windows_defender_status "
            "FROM agent_telemetry WHERE idempotency_key = $1",
            idemp_key_1
        )
        assert t_row is not None
        assert t_row["agent_id"] == enrolled_agent_id

        agent_row = await db_conn.fetchrow("SELECT last_seen FROM agents WHERE id = $1", enrolled_agent_id)
        assert agent_row["last_seen"] is not None

        # 5. Offline Queueing during disconnect
        queue_storage = QueueStorage(queue_path)
        idemp_key_offline = f"tx_live_offline_{int(time.time())}_2"
        offline_payload = {
            "cpu_percent": 15.0,
            "ram_percent": 40.0,
            "ram_used_mb": 6000.0,
            "ram_total_mb": 16000.0,
            "disk_percent": 25.0,
            "disk_used_gb": 60.0,
            "disk_total_gb": 240.0,
            "windows_activation_status": act_info.status,
            "windows_defender_status": def_info.status,
            "idempotency_key": idemp_key_offline,
            "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        queue_storage.enqueue(offline_payload, idempotency_key=idemp_key_offline)
        assert queue_storage.get_stats()["pending"] == 1

        # 6. Flush queue upon reconnect
        sync_worker = QueueSyncWorker(queue_storage, api_client)
        delivered = sync_worker.sync_pending()
        assert delivered == 1
        assert queue_storage.get_stats()["pending"] == 0

        # 7. Verify delivered record in PostgreSQL
        offline_db_row = await db_conn.fetchrow(
            "SELECT id, agent_id, idempotency_key FROM agent_telemetry WHERE idempotency_key = $1",
            idemp_key_offline
        )
        assert offline_db_row is not None

        # 8. Idempotency protection
        dup_resp = api_client.submit_telemetry(offline_payload)
        assert dup_resp.get("is_duplicate") is True
        assert dup_resp.get("status") == "ignored_duplicate"

        count_rows = await db_conn.fetchval(
            "SELECT count(*) FROM agent_telemetry WHERE idempotency_key = $1",
            idemp_key_offline
        )
        assert count_rows == 1

    finally:
        if enrolled_agent_id:
            await db_conn.execute("DELETE FROM agents WHERE id = $1", enrolled_agent_id)
        await db_conn.close()
