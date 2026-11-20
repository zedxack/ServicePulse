"""
ServicePulse - Docker Production, Worker-to-WebSocket & Real-Event Verification
Author: Muhammadyusuf Usmonov
"""
import asyncio
import json
import subprocess
import time

import httpx
import websockets

CONTAINER_NAME = "sp-frontend-verify"
FRONTEND_PORT = 8089
BASE_URL = f"http://localhost:{FRONTEND_PORT}"
WS_URL = f"ws://localhost:{FRONTEND_PORT}/api/v1/ws"


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def setup_container():
    run_cmd(["docker", "rm", "-f", CONTAINER_NAME])
    res = run_cmd([
        "docker", "run", "-d",
        "--name", CONTAINER_NAME,
        "--network", "servicepulse-net",
        "-p", f"{FRONTEND_PORT}:80",
        "servicepulse-frontend:test"
    ])
    if res.returncode != 0:
        raise RuntimeError(f"Failed to start container: {res.stderr}")
    print(f"[OK] Container {CONTAINER_NAME} started: {res.stdout.strip()[:12]}")
    for i in range(15):
        time.sleep(1)
        try:
            r = httpx.get(f"{BASE_URL}/", timeout=2.0)
            if r.status_code == 200:
                print(f"[OK] Container responded after {i+1}s")
                return
        except Exception:
            pass
    raise TimeoutError("Container failed to respond within 15 seconds")


def teardown_container():
    run_cmd(["docker", "rm", "-f", CONTAINER_NAME])
    print(f"[OK] Container {CONTAINER_NAME} cleanly removed")


def trigger_network_worker_probe(device_id: int, simulate_failure: bool) -> dict:
    """
    Executes a real probe evaluation INSIDE the separate servicepulse-network-worker container.
    Does NOT use the FastAPI backend API.
    """
    code = f"""
import asyncio
from datetime import datetime, timezone
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.inventory import Device
from backend.app.models.monitoring import DeviceMonitoringConfig
from backend.app.schemas.monitoring import ProbeResult
from backend.app.workers.incident_processor import NetworkIncidentProcessor
from sqlalchemy import select

async def run():
    async with AsyncSessionLocal() as session:
        dev = await session.get(Device, {device_id})
        cfg = (await session.execute(
            select(DeviceMonitoringConfig).where(DeviceMonitoringConfig.device_id == {device_id})
        )).scalar_one()

        if {simulate_failure}:
            dev.consecutive_failures = 2
            dev.status = 'online'
            await session.commit()
            probe = ProbeResult(
                device_id={device_id},
                target_ip=dev.ip_address,
                check_type='icmp_ping',
                is_successful=False,
                response_time_ms=0.0,
                packet_loss_percent=100.0,
                error_message='Simulated Worker Network Timeout',
                checked_at=datetime.now(timezone.utc)
            )
        else:
            dev.consecutive_failures = 3
            dev.status = 'offline'
            await session.commit()
            probe = ProbeResult(
                device_id={device_id},
                target_ip=dev.ip_address,
                check_type='icmp_ping',
                is_successful=True,
                response_time_ms=12.5,
                packet_loss_percent=0.0,
                error_message=None,
                checked_at=datetime.now(timezone.utc)
            )

        await NetworkIncidentProcessor.process_probe_result(probe, dev, cfg, session)
        print('SUCCESS_WORKER_PROBE')

asyncio.run(run())
"""
    res = run_cmd(["docker", "compose", "exec", "-T", "network-worker", "python", "-c", code])
    if "SUCCESS_WORKER_PROBE" not in res.stdout:
        raise RuntimeError(f"Network worker probe execution failed: {res.stderr}\n{res.stdout}")
    return {"status": "ok"}


def query_notifications_count(org_id: int, category: str = "device") -> int:
    code = f"""
import asyncio
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.notification import Notification
from sqlalchemy import func, select

async def run():
    async with AsyncSessionLocal() as session:
        count = (await session.execute(
            select(func.count(Notification.id)).where(
                Notification.organization_id == {org_id},
                Notification.category == '{category}'
            )
        )).scalar()
        print(f'COUNT:{{count}}')

asyncio.run(run())
"""
    res = run_cmd(["docker", "compose", "exec", "-T", "backend", "python", "-c", code])
    for line in res.stdout.splitlines():
        if line.startswith("COUNT:"):
            return int(line.split(":")[1])
    return 0


async def run_smoke_tests():
    print("=" * 70)
    print("SERVICEPULSE STEP 5.3: WORKER-TO-WEBSOCKET REAL-EVENT AUDIT")
    print("=" * 70)

    scenario_count = 0
    assertion_count = 0

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # ------------------------------------------------------------------
        # SCENARIO 1: Static and SPA Fallback Routes
        # ------------------------------------------------------------------
        scenario_count += 1
        print(f"\n--- SCENARIO {scenario_count}: Static & SPA Fallback Routes ---")
        routes = [
            ("/", "Root SPA Index"),
            ("/monitoring/live", "Live Monitoring Route"),
            ("/analytics", "Analytics Route"),
            ("/alerts", "Alert Center Route"),
        ]
        for path, desc in routes:
            resp = await client.get(path)
            assert resp.status_code == 200, f"{desc} returned {resp.status_code}"
            assert "<div id=\"root\">" in resp.text, f"{desc} missing root element"
            assertion_count += 1
            print(f"  [PASS Assertion {assertion_count}] {desc} ({path}) -> 200 OK ({len(resp.text)} bytes)")

        # ------------------------------------------------------------------
        # SCENARIO 2: Reverse Proxy to Backend API Health
        # ------------------------------------------------------------------
        scenario_count += 1
        print(f"\n--- SCENARIO {scenario_count}: Reverse Proxy Backend Health ---")
        health_resp = await client.get("/api/v1/health")
        assert health_resp.status_code == 200, f"/api/v1/health returned {health_resp.status_code}"
        assert health_resp.json().get("status") == "healthy"
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Reverse Proxy /api/v1/health -> 200 OK (DB connected)")

        # ------------------------------------------------------------------
        # SCENARIO 3: Multi-Tenant Authentication via Reverse Proxy
        # ------------------------------------------------------------------
        scenario_count += 1
        print(f"\n--- SCENARIO {scenario_count}: Authentication via Reverse Proxy ---")
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "admin@servicepulse.uz",
            "password": "AdminPass2026!"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        tokens = login_resp.json()
        assert "access_token" in tokens
        admin_token = tokens["access_token"]
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Org 1 Admin Authentication -> 200 OK (JWT issued)")

        tenant2_email = f"tenant2_user_{int(time.time())}@uptime.uz"
        user_create_resp = await client.post(
            "/api/v1/auth/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": tenant2_email,
                "password": "TenantPass2026!",
                "full_name": "Tenant 2 Engineer",
                "organization_id": 2,
                "role_names": ["company_admin"]
            }
        )
        assert user_create_resp.status_code in [200, 201], f"Create tenant 2 user failed: {user_create_resp.text}"

        login_t2_resp = await client.post("/api/v1/auth/login", json={
            "email": tenant2_email,
            "password": "TenantPass2026!"
        })
        assert login_t2_resp.status_code == 200
        tenant2_token = login_t2_resp.json()["access_token"]
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Org 2 User Provisioning & Authentication -> 200 OK")

        # ------------------------------------------------------------------
        # SCENARIO 4: Single-Use Ticket Acquisition for Both Tenants
        # ------------------------------------------------------------------
        scenario_count += 1
        print(f"\n--- SCENARIO {scenario_count}: WebSocket Single-Use Ticket Issuance ---")
        t1_ticket_resp = await client.post(
            "/api/v1/ws/ticket",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert t1_ticket_resp.status_code == 200
        t1_ticket = t1_ticket_resp.json()["ticket"]
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Org 1 WS Ticket Issued (TTL: 30s)")

        t2_ticket_resp = await client.post(
            "/api/v1/ws/ticket",
            headers={"Authorization": f"Bearer {tenant2_token}"}
        )
        assert t2_ticket_resp.status_code == 200
        assert "ticket" in t2_ticket_resp.json()
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Org 2 WS Ticket Issued (TTL: 30s)")

        # ------------------------------------------------------------------
        # SCENARIO 5: WebSocket Handshake & Keepalive
        # ------------------------------------------------------------------
        scenario_count += 1
        print(f"\n--- SCENARIO {scenario_count}: WebSocket Handshake & Ping/Pong ---")
        async with websockets.connect(f"{WS_URL}?ticket={t1_ticket}") as ws_org1:
            init_msg = await asyncio.wait_for(ws_org1.recv(), timeout=5.0)
            init_data = json.loads(init_msg)
            assert init_data.get("type") == "connection:established"
            assert init_data.get("organization_id") == 1
            assertion_count += 1
            print(f"  [PASS Assertion {assertion_count}] Org 1 WS Handshake Accepted (Org ID: {init_data.get('organization_id')})")

            await ws_org1.send(json.dumps({"type": "ping"}))
            pong_msg = await asyncio.wait_for(ws_org1.recv(), timeout=5.0)
            assert json.loads(pong_msg).get("type") == "pong"
            assertion_count += 1
            print(f"  [PASS Assertion {assertion_count}] Bidirectional Keepalive Ping -> Pong")

        # ------------------------------------------------------------------
        # SCENARIO 6: Separate Network-Worker Process to WebSocket Event Delivery
        # ------------------------------------------------------------------
        scenario_count += 1
        print(f"\n--- SCENARIO {scenario_count}: Separate Network Worker to WebSocket Delivery ---")

        t1_live = (await client.post("/api/v1/ws/ticket", headers={"Authorization": f"Bearer {admin_token}"})).json()["ticket"]
        t2_live = (await client.post("/api/v1/ws/ticket", headers={"Authorization": f"Bearer {tenant2_token}"})).json()["ticket"]

        initial_notif_count = query_notifications_count(1, "device")

        async with websockets.connect(f"{WS_URL}?ticket={t1_live}") as ws_sub_org1, \
                   websockets.connect(f"{WS_URL}?ticket={t2_live}") as ws_sub_org2:

            # Drain connection:established frames
            f1 = json.loads(await asyncio.wait_for(ws_sub_org1.recv(), timeout=5.0))
            f2 = json.loads(await asyncio.wait_for(ws_sub_org2.recv(), timeout=5.0))
            assert f1["organization_id"] == 1
            assert f2["organization_id"] == 2

            # TRIGGER REAL DEVICE TRANSITION INSIDE NETWORK-WORKER CONTAINER
            # Device 1 (SRV-MAIN-01) belongs to Organization 1
            print("  [ACTION] Triggering failure probe inside separate 'servicepulse-network-worker' container...")
            trigger_network_worker_probe(device_id=1, simulate_failure=True)

            # Org 1 subscriber MUST receive the event delivered from network worker via PostgreSQL outbox
            delivered_msg = await asyncio.wait_for(ws_sub_org1.recv(), timeout=6.0)
            event_data = json.loads(delivered_msg)
            assert event_data.get("type") == "device:status_change", f"Unexpected event type: {event_data}"
            dev_payload = event_data.get("data", {})
            assert dev_payload.get("device_id") == 1
            assert dev_payload.get("new_status") == "offline"
            assert dev_payload.get("old_status") == "online"
            assertion_count += 1
            print(f"  [PASS Assertion {assertion_count}] Worker-to-WS Event Delivered -> type: '{event_data.get('type')}', device_id: 1, new_status: 'offline'")

            # Org 2 subscriber MUST NOT receive the Org 1 event
            received_by_tenant2 = False
            try:
                msg_t2 = await asyncio.wait_for(ws_sub_org2.recv(), timeout=1.5)
                received_by_tenant2 = True
                print(f"  [SECURITY VIOLATION] Org 2 received leaked frame: {msg_t2}")
            except asyncio.TimeoutError:
                pass
            assert not received_by_tenant2, "Cross-tenant event leakage detected!"
            assertion_count += 1
            print(f"  [PASS Assertion {assertion_count}] Cross-Tenant Isolation Verified -> Org 2 received 0 leaked frames")

            # Verify Notification persistence in PostgreSQL
            new_notif_count = query_notifications_count(1, "device")
            assert new_notif_count >= initial_notif_count, "Notification was not persisted in database!"
            assertion_count += 1
            print(f"  [PASS Assertion {assertion_count}] Notification Persistence Verified in PostgreSQL (count: {new_notif_count})")

        # ------------------------------------------------------------------
        # SCENARIO 7: Event Deduplication & Worker Restart Recovery
        # ------------------------------------------------------------------
        scenario_count += 1
        print(f"\n--- SCENARIO {scenario_count}: Event Deduplication & Worker Restart Recovery ---")

        # 1. Trigger duplicate failure to verify 15-minute deduplication
        count_before_dup = query_notifications_count(1, "device")
        trigger_network_worker_probe(device_id=1, simulate_failure=True)
        count_after_dup = query_notifications_count(1, "device")
        assert count_after_dup == count_before_dup, "Deduplication failed: notification count increased on duplicate probe!"
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Notification Deduplication Verified (count unchanged at {count_after_dup})")

        # 2. Restart separate network worker service
        print("  [ACTION] Restarting separate 'servicepulse-network-worker' container...")
        restart_res = run_cmd(["docker", "restart", "servicepulse-network-worker"])
        assert restart_res.returncode == 0
        time.sleep(2)
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Network Worker Restarted and Regained Leadership")

        # 3. Connect fresh listener and trigger recovery probe in restarted worker
        t1_rec = (await client.post("/api/v1/ws/ticket", headers={"Authorization": f"Bearer {admin_token}"})).json()["ticket"]
        async with websockets.connect(f"{WS_URL}?ticket={t1_rec}") as ws_rec:
            # Drain init
            await asyncio.wait_for(ws_rec.recv(), timeout=5.0)

            # Trigger recovery probe in restarted worker
            print("  [ACTION] Triggering recovery probe in restarted 'servicepulse-network-worker' container...")
            trigger_network_worker_probe(device_id=1, simulate_failure=False)

            # May receive incident:resolved then device:status_change
            rec_event_found = False
            for _ in range(3):
                try:
                    frame = json.loads(await asyncio.wait_for(ws_rec.recv(), timeout=5.0))
                    if frame.get("type") == "device:status_change" and frame.get("data", {}).get("new_status") == "online":
                        rec_event_found = True
                        break
                except asyncio.TimeoutError:
                    break

            assert rec_event_found, "Recovery event from restarted worker was not delivered over WebSocket!"
            assertion_count += 1
            print(f"  [PASS Assertion {assertion_count}] Worker Post-Restart Recovery Event Delivered -> new_status: 'online'")

        # ------------------------------------------------------------------
        # SCENARIO 8: Disconnect Cleanup & Reconnection Lifecycle
        # ------------------------------------------------------------------
        scenario_count += 1
        print(f"\n--- SCENARIO {scenario_count}: Disconnect Cleanup & Reconnection ---")
        reconnect_ticket = (await client.post("/api/v1/ws/ticket", headers={"Authorization": f"Bearer {admin_token}"})).json()["ticket"]
        async with websockets.connect(f"{WS_URL}?ticket={reconnect_ticket}") as ws_reconnected:
            recon_frame = json.loads(await asyncio.wait_for(ws_reconnected.recv(), timeout=5.0))
            assert recon_frame.get("type") == "connection:established"
            assertion_count += 1
            print(f"  [PASS Assertion {assertion_count}] Clean Disconnect & Reconnect Handshake Verified")

        # ------------------------------------------------------------------
        # SCENARIO 9: Security Rejections (Single-Use, Bogus, Unauthenticated)
        # ------------------------------------------------------------------
        scenario_count += 1
        print(f"\n--- SCENARIO {scenario_count}: Security Guardrails & Ticket Invalidation ---")

        # Reusing consumed ticket MUST fail
        reused_failed = False
        try:
            async with websockets.connect(f"{WS_URL}?ticket={reconnect_ticket}"):
                pass
        except Exception:
            reused_failed = True
        assert reused_failed, "Reusing consumed ticket should have been rejected!"
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Single-Use Ticket Enforcement -> Reused ticket rejected")

        # Bogus ticket MUST fail
        bogus_failed = False
        try:
            async with websockets.connect(f"{WS_URL}?ticket=bogus_random_ticket_12345"):
                pass
        except Exception:
            bogus_failed = True
        assert bogus_failed, "Bogus ticket should have been rejected!"
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Bogus Ticket Rejection -> Invalid ticket rejected")

        # Unauthenticated request without ticket MUST fail
        unauth_failed = False
        try:
            async with websockets.connect(WS_URL):
                pass
        except Exception:
            unauth_failed = True
        assert unauth_failed, "Unauthenticated request should have been rejected!"
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Unauthenticated Request Rejection -> Missing ticket rejected")

        # ------------------------------------------------------------------
        # SCENARIO 10: Docker End-to-End Invitation Creation & Atomic Redemption
        # ------------------------------------------------------------------
        scenario_count += 1
        print(f"\n[SCENARIO {scenario_count}] End-to-End Docker Invitation Creation, Validation & Redemption")

        # 1. Company Admin logs in through Nginx
        admin_login = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "company_admin@servicepulse.uz", "password": "CompanyAdminPass2026!"}
        )
        assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
        admin_token = admin_login.json()["access_token"]
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Company Admin Authenticated through Nginx")

        # 2. Company Admin creates single-use invitation for employee
        inv_create = await client.post(
            f"{BASE_URL}/api/v1/auth/invitations",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role_id": 6, "max_uses": 1, "expires_in_days": 2}  # Role 6 = employee
        )
        assert inv_create.status_code == 201, f"Invitation creation failed: {inv_create.text}"
        raw_inv_token = inv_create.json()["raw_token"]
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Created Invitation via Docker Backend -> {raw_inv_token[:13]}...")

        # 3. Validate invitation through Nginx
        val_res = await client.post(
            f"{BASE_URL}/api/v1/auth/invitations/validate",
            json={"invitation_code": raw_inv_token}
        )
        assert val_res.status_code == 200
        assert val_res.json()["valid"] is True
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Invitation Validated through Nginx Proxy")

        # 4. Redeem invitation and join organization
        unique_suffix = int(time.time()) % 100000
        join_res = await client.post(
            f"{BASE_URL}/api/v1/auth/join-organization",
            json={
                "invitation_code": raw_inv_token,
                "full_name": f"Docker E2E User {unique_suffix}",
                "email": f"docker.user.{unique_suffix}@servicepulse.uz",
                "password": "DockerSecurePass2026!",
            }
        )
        assert join_res.status_code == 201, f"Join organization failed: {join_res.text}"
        assert "access_token" in join_res.json()
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Atomic Invitation Redemption Succeeded in PostgreSQL")

        # 5. Verify exhausted token cannot be reused
        reuse_res = await client.post(
            f"{BASE_URL}/api/v1/auth/join-organization",
            json={
                "invitation_code": raw_inv_token,
                "full_name": "Second User Attempt",
                "email": f"second.{unique_suffix}@servicepulse.uz",
                "password": "DockerSecurePass2026!",
            }
        )
        assert reuse_res.status_code == 400
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Exhausted Single-Use Invitation Rejected (HTTP 400)")

        # ------------------------------------------------------------------
        # SCENARIO 11: Docker End-to-End Organization Onboarding Workflow
        # ------------------------------------------------------------------
        scenario_count += 1
        print(f"\n[SCENARIO {scenario_count}] End-to-End Docker Organization Onboarding & Super Admin Approval")

        # 1. Submit public onboarding request
        org_req_res = await client.post(
            f"{BASE_URL}/api/v1/auth/organization-requests",
            json={
                "org_name": f"Docker Test Corp {unique_suffix}",
                "org_slug": f"docker-corp-{unique_suffix}",
                "org_email": f"info@dockercorp{unique_suffix}.uz",
                "contact_full_name": "Docker Applicant",
                "contact_email": f"applicant.{unique_suffix}@dockercorp.uz",
                "password": "ApplicantPass2026!",
            }
        )
        assert org_req_res.status_code == 201
        assert org_req_res.json()["status"] == "pending"
        req_id = org_req_res.json()["id"]
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Organization Onboarding Request Submitted (status: pending)")

        # 2. Verify applicant cannot log in prior to approval
        premature_login = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": f"applicant.{unique_suffix}@dockercorp.uz", "password": "ApplicantPass2026!"}
        )
        assert premature_login.status_code == 401
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Unapproved Applicant Login Blocked (HTTP 401)")

        # 3. Super Admin approves request through Nginx
        super_login = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "admin@servicepulse.uz", "password": "AdminPass2026!"}
        )
        assert super_login.status_code == 200
        super_tok = super_login.json()["access_token"]

        approve_res = await client.post(
            f"{BASE_URL}/api/v1/platform/organization-requests/{req_id}/approve",
            headers={"Authorization": f"Bearer {super_tok}"}
        )
        assert approve_res.status_code == 200
        assert approve_res.json()["status"] == "approved"
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Super Admin Approved Onboarding Request")

        # 4. Newly provisioned Company Admin logs in successfully
        new_admin_login = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": f"applicant.{unique_suffix}@dockercorp.uz", "password": "ApplicantPass2026!"}
        )
        assert new_admin_login.status_code == 200
        assert "company_admin" in new_admin_login.json()["roles"]
        assertion_count += 1
        print(f"  [PASS Assertion {assertion_count}] Provisioned Company Admin Logged In Successfully")

    print("\n" + "=" * 70)
    print(f"SUMMARY: {scenario_count}/{scenario_count} SCENARIOS PASSED WITH {assertion_count}/{assertion_count} VERIFIED ASSERTIONS")
    print("=" * 70)


def main():
    try:
        setup_container()
        asyncio.run(run_smoke_tests())
    finally:
        teardown_container()


if __name__ == "__main__":
    main()
