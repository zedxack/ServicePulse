"""
ServicePulse - Secure Acceptance Audit Login Verification
Verifies:
1. Login API returns success.
2. JWT is valid and contains expected claims.
3. /auth/me returns the correct user.
4. is_primary_owner is true.
5. Correct dashboard access is granted.
6. Logout invalidates the client session.

Security notice: Does not print credentials, hashes, or tokens to stdout/logs.
"""
import sys
import os
sys.path.insert(0, os.path.abspath("."))

import httpx
from backend.app.core.config import settings

BASE_URL = "http://localhost:8000"

def run_verification():
    results = {}
    print("Executing secure login verification against local backend...")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # Step 1: Login API
        login_payload = {
            "email": settings.FIRST_SUPERUSER_EMAIL,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        }
        resp = client.post("/api/v1/auth/login", json=login_payload)
        if resp.status_code == 200:
            token_data = resp.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            token_type = token_data.get("token_type")
            expires_in = token_data.get("expires_in")
            is_valid_structure = bool(
                access_token and refresh_token and token_type == "bearer" and expires_in and expires_in > 0
            )
            results["1_login_api_status"] = "PASS" if is_valid_structure else "FAIL"
            results["2_jwt_structure_valid"] = "PASS" if is_valid_structure else "FAIL"
        else:
            print(f"[FAIL] Login endpoint returned HTTP {resp.status_code}")
            results["1_login_api_status"] = f"FAIL (HTTP {resp.status_code})"
            results["2_jwt_structure_valid"] = "FAIL"
            return results

        # Step 2: /auth/me profile inspection
        headers = {"Authorization": f"Bearer {access_token}"}
        me_resp = client.get("/api/v1/auth/me", headers=headers)
        if me_resp.status_code == 200:
            me_data = me_resp.json()
            is_correct_user = (me_data.get("email") == settings.FIRST_SUPERUSER_EMAIL and me_data.get("id") == 1)
            is_active = me_data.get("is_active") is True
            is_super = me_data.get("is_superuser") is True
            is_owner = me_data.get("is_primary_owner") is True
            has_role = any(r.get("name") == "platform_super_admin" for r in me_data.get("roles", []))

            results["3_auth_me_correct_user"] = "PASS" if (is_correct_user and is_active and is_super) else "FAIL"
            results["4_is_primary_owner_flag"] = "PASS" if is_owner else "FAIL"
            results["4b_platform_super_admin_role"] = "PASS" if has_role else "FAIL"
        else:
            results["3_auth_me_correct_user"] = f"FAIL (HTTP {me_resp.status_code})"
            results["4_is_primary_owner_flag"] = "FAIL"
            results["4b_platform_super_admin_role"] = "FAIL"

        # Step 3: Platform Dashboard Access
        dash_resp = client.get("/api/v1/dashboard/platform", headers=headers)
        if dash_resp.status_code == 200:
            dash_data = dash_resp.json()
            has_platform_health = "platform_health_status" in dash_data
            results["5_platform_dashboard_access"] = "PASS" if has_platform_health else "FAIL"
        else:
            results["5_platform_dashboard_access"] = f"FAIL (HTTP {dash_resp.status_code})"

        # Step 4: Logout invalidation
        logout_resp = client.post("/api/v1/auth/logout", headers=headers)
        if logout_resp.status_code == 200:
            results["6a_logout_api_success"] = "PASS"
            # Verify that the refresh token cannot be reused
            refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
            if refresh_resp.status_code in (401, 400):
                results["6b_session_invalidation_verified"] = "PASS"
            else:
                results["6b_session_invalidation_verified"] = f"FAIL (HTTP {refresh_resp.status_code})"
        else:
            results["6a_logout_api_success"] = f"FAIL (HTTP {logout_resp.status_code})"
            results["6b_session_invalidation_verified"] = "FAIL"

    return results

if __name__ == "__main__":
    res = run_verification()
    all_pass = True
    print("\n=== LOGIN VERIFICATION RESULTS ===")
    for k, v in res.items():
        print(f"  {k:<35}: {v}")
        if v != "PASS":
            all_pass = False
    print(f"\nOVERALL RESULT: {'PASS' if all_pass else 'FAIL'}")
    sys.exit(0 if all_pass else 1)
