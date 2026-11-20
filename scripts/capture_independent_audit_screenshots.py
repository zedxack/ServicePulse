import asyncio
import base64
import json
import os
import shutil
import subprocess

import httpx
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = r"C:\Projects\ServicePulse\tmp_cdp_profile_audit"
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
    await asyncio.sleep(0.6)
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
    for _ in range(25):
        await asyncio.sleep(0.5)
        url = await eval_js(ws, "window.location.href")
        if url and "/login" not in url:
            break
    print(f"Logged in as {email} -> {url}")
    await asyncio.sleep(1.0)

async def spa_navigate(ws, href, wait_time=2.5):
    nav_script = f"""
    (() => {{
        const link = document.querySelector('a[href="{href}"]');
        if (link) {{
            link.click();
            return 'CLICKED';
        }}
        window.history.pushState(null, '', '{href}');
        window.dispatchEvent(new PopStateEvent('popstate'));
        return 'PUSHED_STATE';
    }})();
    """
    res = await eval_js(ws, nav_script)
    await asyncio.sleep(wait_time)
    curr = await eval_js(ws, "window.location.href")
    print(f"SPA Nav to {href} -> {res} (URL: {curr})")

async def set_theme(ws, target_theme="dark"):
    script = f"""
    (() => {{
        const isCurrentlyDark = document.documentElement.classList.contains('dark');
        if ('{target_theme}' === 'dark' && !isCurrentlyDark) {{
            document.documentElement.classList.add('dark');
            localStorage.setItem('servicepulse-theme', 'dark');
            return 'SWITCHED_TO_DARK';
        }} else if ('{target_theme}' === 'light' && isCurrentlyDark) {{
            document.documentElement.classList.remove('dark');
            localStorage.setItem('servicepulse-theme', 'light');
            return 'SWITCHED_TO_LIGHT';
        }}
        return 'NOOP';
    }})();
    """
    await eval_js(ws, script)
    await asyncio.sleep(0.5)

async def run_extended_captures():
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
            # 1. Super Admin Session
            tab_id, ws_url = await create_tab(client, f"{BASE_URL}/login")
            async with websockets.connect(ws_url, max_size=20*1024*1024) as ws:
                await send_cmd(ws, "Page.enable")
                await send_cmd(ws, "Runtime.enable")
                await login_user(ws, "admin@servicepulse.uz", "AdminPass2026!")

                # 1. Incident Detail
                await spa_navigate(ws, "/incidents/1")
                await set_theme(ws, "dark")
                await capture(ws, "audit_incident_detail_after.png", 1440, 900)
                await capture(ws, "audit_incident_detail_mobile_after.png", 390, 844)
                await set_theme(ws, "light")
                await capture(ws, "audit_incident_detail_after_light.png", 1440, 900)

                # 2. Ticket Detail
                await spa_navigate(ws, "/tickets/1")
                await set_theme(ws, "dark")
                await capture(ws, "audit_ticket_detail_after.png", 1440, 900)
                await capture(ws, "audit_ticket_detail_mobile_after.png", 390, 844)
                await set_theme(ws, "light")
                await capture(ws, "audit_ticket_detail_after_light.png", 1440, 900)

                # 3. Light Theme Versions of Operational Modules
                await spa_navigate(ws, "/inventory")
                await set_theme(ws, "light")
                await capture(ws, "audit_inventory_after_light.png", 1440, 900)

                await spa_navigate(ws, "/incidents")
                await set_theme(ws, "light")
                await capture(ws, "audit_incidents_after_light.png", 1440, 900)
                await capture(ws, "audit_incidents_mobile_after.png", 390, 844)

                await spa_navigate(ws, "/tickets")
                await set_theme(ws, "dark")
                await capture(ws, "audit_tickets_after.png", 1440, 900)
                await set_theme(ws, "light")
                await capture(ws, "audit_tickets_after_light.png", 1440, 900)
                await capture(ws, "audit_tickets_mobile_after.png", 390, 844)

                await spa_navigate(ws, "/software")
                await set_theme(ws, "light")
                await capture(ws, "audit_software_after_light.png", 1440, 900)
                await capture(ws, "audit_software_mobile_after.png", 390, 844)

                await spa_navigate(ws, "/monitoring/live")
                await set_theme(ws, "light")
                await capture(ws, "audit_monitoring_live_after_light.png", 1440, 900)
                await capture(ws, "audit_monitoring_live_mobile_after.png", 390, 844)

                await spa_navigate(ws, "/analytics")
                await set_theme(ws, "light")
                await capture(ws, "audit_analytics_after_light.png", 1440, 900)
                await capture(ws, "audit_analytics_mobile_after.png", 390, 844)

                await spa_navigate(ws, "/alerts")
                await set_theme(ws, "light")
                await capture(ws, "audit_alerts_after_light.png", 1440, 900)
                await capture(ws, "audit_alerts_mobile_after.png", 390, 844)

            await close_tab(client, tab_id)

            # 2. Light Theme Dashboards
            # Company Admin Light
            tab_id, ws_url = await create_tab(client, f"{BASE_URL}/login")
            async with websockets.connect(ws_url, max_size=20*1024*1024) as ws:
                await send_cmd(ws, "Page.enable")
                await send_cmd(ws, "Runtime.enable")
                await login_user(ws, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
                await spa_navigate(ws, "/dashboard/company")
                await set_theme(ws, "light")
                await capture(ws, "audit_dashboard_company_after_light.png", 1440, 900)
            await close_tab(client, tab_id)

            # SysAdmin Light
            tab_id, ws_url = await create_tab(client, f"{BASE_URL}/login")
            async with websockets.connect(ws_url, max_size=20*1024*1024) as ws:
                await send_cmd(ws, "Page.enable")
                await send_cmd(ws, "Runtime.enable")
                await login_user(ws, "support@servicepulse.uz", "SupportPass2026!")
                await spa_navigate(ws, "/dashboard/sysadmin")
                await set_theme(ws, "light")
                await capture(ws, "audit_dashboard_sysadmin_after_light.png", 1440, 900)
            await close_tab(client, tab_id)

            # Executive Light
            tab_id, ws_url = await create_tab(client, f"{BASE_URL}/login")
            async with websockets.connect(ws_url, max_size=20*1024*1024) as ws:
                await send_cmd(ws, "Page.enable")
                await send_cmd(ws, "Runtime.enable")
                await login_user(ws, "executive@servicepulse.uz", "ExecutivePass2026!")
                await spa_navigate(ws, "/dashboard/executive")
                await set_theme(ws, "light")
                await capture(ws, "audit_dashboard_executive_after_light.png", 1440, 900)
            await close_tab(client, tab_id)

            # Employee Light
            tab_id, ws_url = await create_tab(client, f"{BASE_URL}/login")
            async with websockets.connect(ws_url, max_size=20*1024*1024) as ws:
                await send_cmd(ws, "Page.enable")
                await send_cmd(ws, "Runtime.enable")
                await login_user(ws, "employee@servicepulse.uz", "EmployeePass2026!")
                await spa_navigate(ws, "/dashboard/employee")
                await set_theme(ws, "light")
                await capture(ws, "audit_dashboard_employee_after_light.png", 1440, 900)
            await close_tab(client, tab_id)

        print("Extended audit captures completed successfully!")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(run_extended_captures())
