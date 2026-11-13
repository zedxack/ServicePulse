"""
ServicePulse - Authentication & RBAC API Integration Tests
Author: Muhammadyusuf Usmonov
"""
import pytest
from httpx import AsyncClient

from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Verify login with valid credentials returns JWT token pair."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.FIRST_SUPERUSER_EMAIL, "password": settings.FIRST_SUPERUSER_PASSWORD}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Verify login fails with invalid password or unknown email."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.FIRST_SUPERUSER_EMAIL, "password": "WrongPassword2026!"}
    )
    assert resp.status_code == 401
    assert "Incorrect email or password" in resp.json()["detail"]

    resp2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@servicepulse.uz", "password": "AnyPassword!"}
    )
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_profile(client: AsyncClient):
    """Verify /auth/me returns profile for authenticated user and 401 without token."""
    # Unauthorized attempt
    resp_unauth = await client.get("/api/v1/auth/me")
    assert resp_unauth.status_code == 401

    # Authorized attempt
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.FIRST_SUPERUSER_EMAIL, "password": settings.FIRST_SUPERUSER_PASSWORD}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    user_data = resp.json()
    assert user_data["email"] == settings.FIRST_SUPERUSER_EMAIL
    assert user_data["is_superuser"] is True
    assert any(r["name"] == "admin" for r in user_data["roles"])


@pytest.mark.asyncio
async def test_token_refresh_and_rotation(client: AsyncClient):
    """Verify refresh token rotation and revocation of previous token."""
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.FIRST_SUPPORT_EMAIL, "password": settings.FIRST_SUPPORT_PASSWORD}
    )
    refresh_tok_1 = login_resp.json()["refresh_token"]

    # First refresh
    ref_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_tok_1}
    )
    assert ref_resp.status_code == 200
    ref_data = ref_resp.json()
    assert "access_token" in ref_data
    refresh_tok_2 = ref_data["refresh_token"]
    assert refresh_tok_2 != refresh_tok_1


@pytest.mark.asyncio
async def test_logout_revokes_tokens(client: AsyncClient):
    """Verify logout revokes active refresh tokens."""
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.FIRST_EMPLOYEE_EMAIL, "password": settings.FIRST_EMPLOYEE_PASSWORD}
    )
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    logout_resp = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == 200


@pytest.mark.asyncio
async def test_rbac_user_management_boundaries(client: AsyncClient):
    """Verify only admin can create new users; employee is forbidden."""
    # 1. Login as employee
    emp_login = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.FIRST_EMPLOYEE_EMAIL, "password": settings.FIRST_EMPLOYEE_PASSWORD}
    )
    emp_headers = {"Authorization": f"Bearer {emp_login.json()['access_token']}"}

    # Employee tries to create a user -> 403 Forbidden
    create_payload = {
        "email": "newuser@servicepulse.uz",
        "full_name": "New Employee",
        "password": "SecurePassword2026!",
        "role_names": ["employee"]
    }
    resp_forbidden = await client.post("/api/v1/auth/users", json=create_payload, headers=emp_headers)
    assert resp_forbidden.status_code == 403

    # 2. Login as admin -> 201 Created
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.FIRST_SUPERUSER_EMAIL, "password": settings.FIRST_SUPERUSER_PASSWORD}
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    resp_created = await client.post("/api/v1/auth/users", json=create_payload, headers=admin_headers)
    assert resp_created.status_code == 201
    created_user = resp_created.json()
    assert created_user["email"] == "newuser@servicepulse.uz"
    assert created_user["is_active"] is True

    # 3. Admin updates status to inactive
    resp_deact = await client.patch(
        f"/api/v1/auth/users/{created_user['id']}/status",
        json={"is_active": False},
        headers=admin_headers
    )
    assert resp_deact.status_code == 200
    assert resp_deact.json()["is_active"] is False
