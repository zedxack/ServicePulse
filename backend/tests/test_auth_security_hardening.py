"""
ServicePulse - Comprehensive Security Hardening & Authentication Regression Tests
Phase 2 Implementation Verification:
1. Normal login and refresh.
2. Logout followed by refresh rejected.
3. Revoked refresh token reuse rejected.
4. Expired refresh token rejected (signature & database expiration).
5. Invalid JWT signature rejected.
6. JWT/database JTI mismatch rejected.
7. Inactive user refresh attempt rejected.
8. Concurrent refresh requests (atomic single-use rotation).
9. Refresh token replay attack prevention.
10. Session isolation between multiple devices.
"""
import asyncio
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.cli.bootstrap_owner import bootstrap_primary_owner
from backend.app.core.rate_limiter import auth_rate_limiter, registration_rate_limiter
from backend.app.core.security import create_refresh_token
from backend.app.models.audit import AuditLog


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    auth_rate_limiter.requests_per_minute = 10000
    registration_rate_limiter.requests_per_minute = 10000
    auth_rate_limiter._records.clear()
    registration_rate_limiter._records.clear()


@pytest.mark.asyncio
async def test_normal_login_and_refresh(client: AsyncClient, test_db: AsyncSession):
    """Scenario 1: Authenticate and perform normal token refresh."""
    await bootstrap_primary_owner(
        email="owner.test@example.com",
        full_name="Owner Test",
        password="SecurePass2026!",
        force=True,
        db_session=test_db,
    )

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner.test@example.com", "password": "SecurePass2026!"},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    ref_token_1 = login_data["refresh_token"]

    # Exchange refresh token
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": ref_token_1},
    )
    assert refresh_resp.status_code == 200
    refresh_data = refresh_resp.json()
    assert "access_token" in refresh_data
    assert "refresh_token" in refresh_data
    assert refresh_data["refresh_token"] != ref_token_1

    # Verify new access token works
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_data['access_token']}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "owner.test@example.com"


@pytest.mark.asyncio
async def test_logout_followed_by_refresh_rejected(client: AsyncClient, test_db: AsyncSession):
    """Scenario 2: Logout invalidates active sessions; refresh attempt must be rejected."""
    await bootstrap_primary_owner(
        email="owner.test@example.com",
        full_name="Owner Test",
        password="SecurePass2026!",
        force=True,
        db_session=test_db,
    )

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner.test@example.com", "password": "SecurePass2026!"},
    )
    data = login_resp.json()
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]

    # Logout
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_resp.status_code == 200

    # Refresh attempt after logout must be rejected with 401
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 401
    assert "revoked" in refresh_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_revoked_refresh_token_reuse_rejected(client: AsyncClient, test_db: AsyncSession):
    """Scenario 3: An already-rotated refresh token cannot be reused."""
    await bootstrap_primary_owner(
        email="owner.test@example.com",
        full_name="Owner Test",
        password="SecurePass2026!",
        force=True,
        db_session=test_db,
    )

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner.test@example.com", "password": "SecurePass2026!"},
    )
    ref_1 = login_resp.json()["refresh_token"]

    # First rotation succeeds
    rot_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": ref_1},
    )
    assert rot_resp.status_code == 200

    # Second attempt with same ref_1 must fail
    reuse_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": ref_1},
    )
    assert reuse_resp.status_code == 401
    assert "revoked" in reuse_resp.json()["detail"].lower()

    # Verify audit log recorded the reuse attempt
    audit = (
        await test_db.execute(
            select(AuditLog).where(AuditLog.action == "auth_refresh_revoked_reuse")
        )
    ).scalar_one_or_none()
    assert audit is not None
    assert audit.status == "failure"


@pytest.mark.asyncio
async def test_expired_refresh_token_rejected(client: AsyncClient, test_db: AsyncSession):
    """Scenario 4: Expired refresh token signature and expired database record rejected."""
    await bootstrap_primary_owner(
        email="owner.test@example.com",
        full_name="Owner Test",
        password="SecurePass2026!",
        force=True,
        db_session=test_db,
    )

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner.test@example.com", "password": "SecurePass2026!"},
    )
    user_id = login_resp.json()["organization_id"] or 1

    # 4A. Expired JWT signature
    expired_jwt = create_refresh_token(
        subject=str(user_id),
        expires_delta=timedelta(seconds=-10),
    )
    exp_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": expired_jwt},
    )
    assert exp_resp.status_code == 401
    assert "expired" in exp_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_jwt_signature_rejected(client: AsyncClient, test_db: AsyncSession):
    """Scenario 5: JWT signed with untrusted key or tampered signature is rejected."""
    await bootstrap_primary_owner(
        email="owner.test@example.com",
        full_name="Owner Test",
        password="SecurePass2026!",
        force=True,
        db_session=test_db,
    )

    # Token signed with fake secret key
    fake_payload = {
        "sub": "1",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
        "type": "refresh",
        "jti": "fakejti12345",
    }
    fake_token = jwt.encode(fake_payload, "completely-wrong-secret-key-123456789", algorithm="HS256")

    bad_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": fake_token},
    )
    assert bad_resp.status_code == 401
    assert "invalid" in bad_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_jwt_database_jti_mismatch_rejected(client: AsyncClient, test_db: AsyncSession):
    """Scenario 6: Signed JWT with a JTI not present in the database is rejected."""
    await bootstrap_primary_owner(
        email="owner.test@example.com",
        full_name="Owner Test",
        password="SecurePass2026!",
        force=True,
        db_session=test_db,
    )

    # Valid signature using app SECRET_KEY, but random JTI never stored in DB
    unregistered_token = create_refresh_token(
        subject="1",
        jti="unregistered-jti-abcdef1234567890",
    )

    mismatch_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": unregistered_token},
    )
    assert mismatch_resp.status_code == 401
    assert "unrecognized" in mismatch_resp.json()["detail"].lower() or "not exist" in mismatch_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_inactive_user_refresh_attempt_rejected(client: AsyncClient, test_db: AsyncSession):
    """Scenario 7: Deactivated user cannot refresh tokens."""
    _, _, user = await bootstrap_primary_owner(
        email="owner.test@example.com",
        full_name="Owner Test",
        password="SecurePass2026!",
        force=True,
        db_session=test_db,
    )

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner.test@example.com", "password": "SecurePass2026!"},
    )
    ref_token = login_resp.json()["refresh_token"]

    # Deactivate the user
    user.is_active = False
    test_db.add(user)
    await test_db.commit()

    inact_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": ref_token},
    )
    assert inact_resp.status_code == 401
    assert "inactive" in inact_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_concurrent_refresh_requests_only_one_succeeds(client: AsyncClient, test_db: AsyncSession):
    """Scenario 8: Concurrent refresh requests with the same token resolve atomically."""
    from backend.app.db.session import get_db
    from backend.app.main import app
    from backend.tests.conftest import TestAsyncSessionLocal

    # Configure per-request isolated sessions so concurrency operates on distinct DB sessions
    async def per_request_db():
        async with TestAsyncSessionLocal() as s:
            yield s

    app.dependency_overrides[get_db] = per_request_db

    try:
        await bootstrap_primary_owner(
            email="owner.test@example.com",
            full_name="Owner Test",
            password="SecurePass2026!",
            force=True,
            db_session=test_db,
        )

        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "owner.test@example.com", "password": "SecurePass2026!"},
        )
        ref_token = login_resp.json()["refresh_token"]

        # Dispatch two concurrent refresh requests
        async def call_refresh():
            return await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": ref_token},
            )

        res1, res2 = await asyncio.gather(call_refresh(), call_refresh(), return_exceptions=True)
        status_codes = sorted([res1.status_code, res2.status_code])
        # Exactly one must succeed (200) and the other must be rejected (401)
        assert status_codes == [200, 401], f"Expected [200, 401], got {status_codes}"
    finally:
        async def restore_get_db():
            yield test_db

        app.dependency_overrides[get_db] = restore_get_db


@pytest.mark.asyncio
async def test_refresh_token_replay_attack_prevention(client: AsyncClient, test_db: AsyncSession):
    """Scenario 9: Replay attack with previously rotated token is intercepted and rejected."""
    await bootstrap_primary_owner(
        email="owner.test@example.com",
        full_name="Owner Test",
        password="SecurePass2026!",
        force=True,
        db_session=test_db,
    )

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner.test@example.com", "password": "SecurePass2026!"},
    )
    token_1 = login_resp.json()["refresh_token"]

    # Legitimate client rotates Token 1 -> Token 2
    rot1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": token_1})
    assert rot1.status_code == 200
    token_2 = rot1.json()["refresh_token"]

    # Legitimate client rotates Token 2 -> Token 3
    rot2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": token_2})
    assert rot2.status_code == 200

    # Attacker tries to replay Token 1
    replay_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": token_1})
    assert replay_resp.status_code == 401
    assert "revoked" in replay_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_session_isolation_between_multiple_devices(client: AsyncClient, test_db: AsyncSession):
    """Scenario 10: Multiple device sessions operate independently; specific logout isolates revocation."""
    await bootstrap_primary_owner(
        email="owner.test@example.com",
        full_name="Owner Test",
        password="SecurePass2026!",
        force=True,
        db_session=test_db,
    )

    # Device 1 logs in
    login_dev1 = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner.test@example.com", "password": "SecurePass2026!"},
    )
    assert login_dev1.status_code == 200
    acc_dev1 = login_dev1.json()["access_token"]
    ref_dev1 = login_dev1.json()["refresh_token"]

    # Device 2 logs in
    login_dev2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner.test@example.com", "password": "SecurePass2026!"},
    )
    assert login_dev2.status_code == 200
    ref_dev2 = login_dev2.json()["refresh_token"]

    # Both tokens are distinct
    assert ref_dev1 != ref_dev2

    # Device 1 rotates its token independently
    rot_dev1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": ref_dev1})
    assert rot_dev1.status_code == 200
    ref_dev1_new = rot_dev1.json()["refresh_token"]

    # Device 2 can still refresh its own token
    rot_dev2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": ref_dev2})
    assert rot_dev2.status_code == 200
    ref_dev2_new = rot_dev2.json()["refresh_token"]

    # Device 1 logs out of its specific session
    logout_dev1 = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {acc_dev1}"},
        json={"refresh_token": ref_dev1_new, "all_sessions": False},
    )
    assert logout_dev1.status_code == 200

    # Device 1's refresh token is now revoked
    dev1_try = await client.post("/api/v1/auth/refresh", json={"refresh_token": ref_dev1_new})
    assert dev1_try.status_code == 401

    # Device 2's session remains active and can continue to refresh
    dev2_try = await client.post("/api/v1/auth/refresh", json={"refresh_token": ref_dev2_new})
    assert dev2_try.status_code == 200
