"""
ServicePulse - Platform Owner & Centralized Access Governance Screenshot Capture
Captures:
- Sign In tab at 1366x768, 1440x900, 390x844 with clean branding
- Join Organization tab with neutral placeholders
- Register New Organization tab with clean empty state
- Owner Access Governance tab inside Platform Super Admin Dashboard
- Inspection Modal (aria-modal="true", role="dialog")
- Approve Confirmation Modal
- Reject Modal with mandatory reason
"""
import asyncio
import base64
import json
import os
import shutil
import subprocess

import httpx
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = r"C:\Projects\ServicePulse\tmp_cdp_profile_governance"
OUTPUT_DIR = r"C:\Projects\ServicePulse\docs\screenshots"
BASE_URL = "http://localhost:5173"

cmd_id = 0


async def send_cmd(ws, method, params=None):
    global cmd_id
    cmd_id += 1
    my_id = cmd_id
    payload = {"id": my_id, "method": method}
    if params:
        payload["params"] = params
    await ws.send(json.dumps(payload))
    while True:
        resp = json.loads(await ws.recv())
        if resp.get("id") == my_id:
            return resp


async def eval_js(ws, expr):
    resp = await send_cmd(ws, "Runtime.evaluate", {
        "expression": expr,
        "awaitPromise": True,
        "returnByValue": True
    })
    return resp.get("result", {}).get("result", {}).get("value")


async def capture(ws, filename, width=1440, height=900):
    await send_cmd(ws, "Emulation.setDeviceMetricsOverride", {
        "width": width,
        "height": height,
        "deviceScaleFactor": 1,
        "mobile": width < 600
    })
    await asyncio.sleep(0.7)
    shot_resp = await send_cmd(ws, "Page.captureScreenshot", {"format": "png"})
    img_bytes = base64.b64decode(shot_resp["result"]["data"])
    out_path = os.path.join(OUTPUT_DIR, filename)
    with open(out_path, "wb") as f:
        f.write(img_bytes)
    print(f"Captured {filename} ({width}x{height}, {len(img_bytes)} bytes)")


async def create_tab(client, url=f"{BASE_URL}/login"):
    new_tab = await client.put(f"http://127.0.0.1:9222/json/new?{url}")
    tab_data = new_tab.json()
    return tab_data["id"], tab_data["webSocketDebuggerUrl"]


async def close_tab(client, tab_id):
    try:
        await client.get(f"http://127.0.0.1:9222/json/close/{tab_id}")
    except Exception:
        pass


async def run_governance_captures():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if os.path.exists(USER_DATA_DIR):
        try:
            shutil.rmtree(USER_DATA_DIR)
        except Exception:
            pass

    proc = subprocess.Popen([
        CHROME_PATH,
        "--remote-debugging-port=9222",
        "--headless=new",
        f"--user-data-dir={USER_DATA_DIR}",
        "--disable-gpu",
        "--window-size=1440,900"
    ])

    try:
        await asyncio.sleep(2.0)
        async with httpx.AsyncClient() as client:
            # -------------------------------------------------------------
            # Part 1: Auth Pages (Sign In, Join, Register)
            # -------------------------------------------------------------
            tab_id, ws_url = await create_tab(client, f"{BASE_URL}/login")
            async with websockets.connect(ws_url, max_size=20 * 1024 * 1024) as ws:
                await send_cmd(ws, "Page.enable")
                await send_cmd(ws, "Runtime.enable")
                await asyncio.sleep(1.5)

                # Set dark theme for consistent screenshots
                await eval_js(ws, "document.documentElement.classList.add('dark'); localStorage.setItem('servicepulse-theme', 'dark');")
                await asyncio.sleep(0.5)

                # 1. Sign In 1366x768
                await capture(ws, "auth_signin_1366x768.png", 1366, 768)

                # 2. Sign In 1440x900
                await capture(ws, "auth_signin_1440x900.png", 1440, 900)

                # 3. Sign In 390x844 (Mobile)
                await capture(ws, "auth_signin_390x844.png", 390, 844)

                # Reset to 1440x900
                await send_cmd(ws, "Emulation.setDeviceMetricsOverride", {
                    "width": 1440,
                    "height": 900,
                    "deviceScaleFactor": 1,
                    "mobile": False
                })

                # 4. Join Organization tab
                await eval_js(ws, """
                (() => {
                    const btn = document.querySelector('[data-testid="tab-join"]');
                    if (btn) btn.click();
                })();
                """)
                await asyncio.sleep(1.0)
                await capture(ws, "auth_join_org_clean.png", 1440, 900)

                # 5. Register New Organization tab
                await eval_js(ws, """
                (() => {
                    const btn = document.querySelector('[data-testid="tab-register-org"]');
                    if (btn) btn.click();
                })();
                """)
                await asyncio.sleep(1.0)
                await capture(ws, "auth_register_org_clean.png", 1440, 900)

                # -------------------------------------------------------------
                # Part 2: Log In as Primary Platform Owner & Platform Dashboard
                # -------------------------------------------------------------
                # Switch back to Sign In
                await eval_js(ws, """
                (() => {
                    const btn = document.querySelector('[data-testid="tab-login"]');
                    if (btn) btn.click();
                })();
                """)
                await asyncio.sleep(1.0)
                await asyncio.sleep(0.5)

                # Fill credentials for admin@servicepulse.uz
                await eval_js(ws, """
                (() => {
                    const setVal = (el, val) => {
                        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        setter.call(el, val);
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                    };
                    const emailInput = document.querySelector('input[type="email"]');
                    const passInput = document.querySelector('input[type="password"]');
                    const btn = document.querySelector('button[data-testid="login-submit-btn"]');
                    if (emailInput && passInput && btn) {
                        setVal(emailInput, 'admin@servicepulse.uz');
                        setVal(passInput, 'AdminPass2026!');
                        btn.click();
                    }
                })();
                """)

                # Wait for navigation to dashboard
                for _ in range(30):
                    await asyncio.sleep(0.5)
                    url = await eval_js(ws, "window.location.href")
                    if url and "/login" not in url:
                        break
                print(f"Logged in as Primary Owner -> {url}")
                await asyncio.sleep(1.5)

                # Ensure on /dashboard/platform with governance tab
                await eval_js(ws, """
                (() => {
                    const tabs = Array.from(document.querySelectorAll('button'));
                    const govTab = tabs.find(b => b.textContent.includes('Access Governance'));
                    if (govTab) {
                        govTab.click();
                    } else {
                        window.history.pushState(null, '', '/dashboard/platform?tab=governance');
                        window.dispatchEvent(new PopStateEvent('popstate'));
                    }
                })();
                """)
                await asyncio.sleep(2.0)

                # 6. Owner Access Governance Overview
                await capture(ws, "owner_governance_overview.png", 1440, 900)

                # 7. Inspection Modal
                await eval_js(ws, """
                (() => {
                    const inspectBtn = document.querySelector('button[title="Inspect Details"]');
                    if (inspectBtn) inspectBtn.click();
                })();
                """)
                await asyncio.sleep(1.0)
                await capture(ws, "owner_governance_inspect_modal.png", 1440, 900)

                # Close inspection modal
                await eval_js(ws, """
                (() => {
                    const closeBtn = document.querySelector('div[role="dialog"] button[aria-label="Close"]') ||
                                     document.querySelector('div[role="dialog"] button');
                    if (closeBtn) closeBtn.click();
                })();
                """)
                await asyncio.sleep(0.8)

                # 8. Approve Confirmation Modal
                await eval_js(ws, """
                (() => {
                    const approveBtn = document.querySelector('button[title="Approve Request"]');
                    if (approveBtn) approveBtn.click();
                })();
                """)
                await asyncio.sleep(1.0)
                await capture(ws, "owner_governance_approve_modal.png", 1440, 900)

                # Cancel approve modal
                await eval_js(ws, """
                (() => {
                    const cancelBtn = Array.from(document.querySelectorAll('div[role="dialog"] button')).find(b => b.textContent.includes('Cancel'));
                    if (cancelBtn) cancelBtn.click();
                })();
                """)
                await asyncio.sleep(0.8)

                # 9. Reject Modal with Reason Input
                await eval_js(ws, """
                (() => {
                    const rejectBtn = document.querySelector('button[title="Reject Request"]');
                    if (rejectBtn) rejectBtn.click();
                })();
                """)
                await asyncio.sleep(1.0)

                # Fill rejection reason
                await eval_js(ws, """
                (() => {
                    const textarea = document.querySelector('div[role="dialog"] textarea');
                    if (textarea) {
                        const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                        setter.call(textarea, 'Candidate security clearance requirements not satisfied for administrative role.');
                        textarea.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                })();
                """)
                await asyncio.sleep(0.8)
                await capture(ws, "owner_governance_reject_modal.png", 1440, 900)

                # Cancel reject modal
                await eval_js(ws, """
                (() => {
                    const cancelBtn = Array.from(document.querySelectorAll('div[role="dialog"] button')).find(b => b.textContent.includes('Cancel'));
                    if (cancelBtn) cancelBtn.click();
                })();
                """)
                await asyncio.sleep(0.5)

            await close_tab(client, tab_id)

        print("All Platform Owner & Access Governance screenshots captured successfully!")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(run_governance_captures())
