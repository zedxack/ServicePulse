import asyncio
import base64
import json
import os
import shutil
import subprocess

import httpx
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = r"C:\Projects\ServicePulse\tmp_cdp_profile"
OUTPUT_DIR = r"C:\Projects\ServicePulse\docs\screenshots"
BASE_URL = "http://localhost"

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
    await asyncio.sleep(0.5)
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

async def login_user(ws, email, password):
    await asyncio.sleep(1.5)
    login_script = f"""
    (() => {{
        const setVal = (el, val) => {{
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(el, val);
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }};
        const emailInput = document.querySelector('input[type="email"]');
        const passInput = document.querySelector('input[type="password"]');
        const btn = document.querySelector('button[data-testid="login-submit-btn"]');
        if (emailInput && passInput && btn) {{
            setVal(emailInput, '{email}');
            setVal(passInput, '{password}');
            btn.click();
            return true;
        }}
        return false;
    }})();
    """
    await eval_js(ws, login_script)
    for _ in range(20):
        await asyncio.sleep(0.5)
        url = await eval_js(ws, "window.location.href")
        if url and "/login" not in url:
            break
    print(f"Logged in as {email} -> {url}")

async def spa_navigate(ws, href, wait_time=2.5):
    # Click link matching href in sidebar or document
    nav_script = f"""
    (() => {{
        const link = document.querySelector('a[href="{href}"]');
        if (link) {{
            link.click();
            return 'CLICKED';
        }}
        // Fallback to window navigation if link is hidden in mobile menu
        window.history.pushState(null, '', '{href}');
        window.dispatchEvent(new PopStateEvent('popstate'));
        return 'PUSHED_STATE';
    }})();
    """
    res = await eval_js(ws, nav_script)
    await asyncio.sleep(wait_time)
    curr = await eval_js(ws, "window.location.href")
    print(f"SPA Nav to {href} -> {res} (URL: {curr})")

async def run_audit_capture():
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
        await asyncio.sleep(1.5)
        async with httpx.AsyncClient() as client:
            # 1. Unauthenticated Login Flows
            tab_id, ws_url = await create_tab(client, f"{BASE_URL}/login")
            async with websockets.connect(ws_url, max_size=20*1024*1024) as ws:
                await send_cmd(ws, "Page.enable")
                await send_cmd(ws, "Runtime.enable")
                await asyncio.sleep(2.0)

                await capture(ws, "audit_login_before.png", 1440, 900)
                await capture(ws, "audit_login_mobile_before.png", 390, 844)

                # Join Tab
                await eval_js(ws, "document.querySelector('[data-testid=\"tab-join\"]').click()")
                await asyncio.sleep(1.0)
                await capture(ws, "audit_login_join_before.png", 1440, 900)

                # Register Org Tab
                await eval_js(ws, "document.querySelector('[data-testid=\"tab-register-org\"]').click()")
                await asyncio.sleep(1.0)
                await capture(ws, "audit_login_org_request_before.png", 1440, 900)
            await close_tab(client, tab_id)

            # 2. Super Admin Session (Platform Dashboard & Operations)
            tab_id, ws_url = await create_tab(client, f"{BASE_URL}/login")
            async with websockets.connect(ws_url, max_size=20*1024*1024) as ws:
                await send_cmd(ws, "Page.enable")
                await send_cmd(ws, "Runtime.enable")
                await login_user(ws, "admin@servicepulse.uz", "AdminPass2026!")

                # Platform Dashboard
                await spa_navigate(ws, "/dashboard/platform")
                await capture(ws, "audit_dashboard_platform_before.png", 1440, 900)
                await capture(ws, "audit_dashboard_platform_mobile_before.png", 390, 844)

                # Inventory
                await spa_navigate(ws, "/inventory")
                await capture(ws, "audit_inventory_before.png", 1440, 900)
                await capture(ws, "audit_inventory_mobile_before.png", 390, 844)

                # Incidents
                await spa_navigate(ws, "/incidents")
                await capture(ws, "audit_incidents_before.png", 1440, 900)

                # Tickets / Helpdesk
                await spa_navigate(ws, "/tickets")
                await capture(ws, "audit_tickets_before.png", 1440, 900)

                # Software Approval
                await spa_navigate(ws, "/software")
                await capture(ws, "audit_software_before.png", 1440, 900)

                # Live Monitoring
                await spa_navigate(ws, "/monitoring/live")
                await capture(ws, "audit_monitoring_live_before.png", 1440, 900)

                # Analytics & SLA
                await spa_navigate(ws, "/analytics")
                await capture(ws, "audit_analytics_before.png", 1440, 900)

                # Alert Center
                await spa_navigate(ws, "/alerts")
                await capture(ws, "audit_alerts_before.png", 1440, 900)
            await close_tab(client, tab_id)

            # 3. Company Admin Session
            tab_id, ws_url = await create_tab(client, f"{BASE_URL}/login")
            async with websockets.connect(ws_url, max_size=20*1024*1024) as ws:
                await send_cmd(ws, "Page.enable")
                await send_cmd(ws, "Runtime.enable")
                await login_user(ws, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
                await spa_navigate(ws, "/dashboard/company")
                await capture(ws, "audit_dashboard_company_before.png", 1440, 900)
            await close_tab(client, tab_id)

            # 4. IT Admin / SysAdmin Session
            tab_id, ws_url = await create_tab(client, f"{BASE_URL}/login")
            async with websockets.connect(ws_url, max_size=20*1024*1024) as ws:
                await send_cmd(ws, "Page.enable")
                await send_cmd(ws, "Runtime.enable")
                await login_user(ws, "support@servicepulse.uz", "SupportPass2026!")
                await spa_navigate(ws, "/dashboard/sysadmin")
                await capture(ws, "audit_dashboard_sysadmin_before.png", 1440, 900)
            await close_tab(client, tab_id)

            # 5. Executive Session
            tab_id, ws_url = await create_tab(client, f"{BASE_URL}/login")
            async with websockets.connect(ws_url, max_size=20*1024*1024) as ws:
                await send_cmd(ws, "Page.enable")
                await send_cmd(ws, "Runtime.enable")
                await login_user(ws, "executive@servicepulse.uz", "ExecutivePass2026!")
                await spa_navigate(ws, "/dashboard/executive")
                await capture(ws, "audit_dashboard_executive_before.png", 1440, 900)
            await close_tab(client, tab_id)

            # 6. Employee Session
            tab_id, ws_url = await create_tab(client, f"{BASE_URL}/login")
            async with websockets.connect(ws_url, max_size=20*1024*1024) as ws:
                await send_cmd(ws, "Page.enable")
                await send_cmd(ws, "Runtime.enable")
                await login_user(ws, "employee@servicepulse.uz", "EmployeePass2026!")
                await spa_navigate(ws, "/dashboard/employee")
                await capture(ws, "audit_dashboard_employee_before.png", 1440, 900)
            await close_tab(client, tab_id)

        print("All audit screenshots captured successfully!")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(run_audit_capture())
