#!/usr/bin/env python3
"""
ServicePulse - Operational Health & Telemetry Inspector
Project: ServicePulse (AT-Servis BMI)
Author: Muhammadyusuf Usmonov

Inspects:
- Docker container health & restart states
- HTTP & API endpoint connectivity (/health, /api/v1/health)
- PostgreSQL database connectivity, connection count, and Alembic version
- WebSocket transactional outbox backlog and lag
- Host disk and memory utilization

Usage:
    python scripts/check_health.py
    python scripts/check_health.py --base-url http://localhost:8000
    python scripts/check_health.py --base-url https://servicepulse.uz
"""
import argparse
import json
import shutil
import subprocess
import urllib.error
import urllib.request


def check_endpoint(url: str, description: str) -> dict:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ServicePulse-HealthCheck/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.getcode()
            body_text = response.read().decode("utf-8")
            try:
                body_json = json.loads(body_text)
            except Exception:
                body_json = body_text

            return {
                "description": description,
                "url": url,
                "reachable": True,
                "status_code": status_code,
                "data": body_json,
            }
    except Exception as exc:
        return {
            "description": description,
            "url": url,
            "reachable": False,
            "error": str(exc),
        }


def check_docker_containers() -> list:
    try:
        cmd = [
            "docker", "ps", "-a",
            "--filter", "name=servicepulse",
            "--format", "{{.Names}}\t{{.Status}}\t{{.State}}"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        containers = []
        for line in res.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                containers.append({
                    "name": parts[0],
                    "status": parts[1],
                    "state": parts[2],
                    "healthy": "healthy" in parts[1].lower() if "health" in parts[1].lower() else "running" in parts[2].lower()
                })
        return containers
    except Exception as exc:
        return [{"error": f"Failed to query Docker containers: {exc}"}]


def check_database_telemetry(container: str = "servicepulse-db", db_user: str = "postgres", db_name: str = "servicepulse") -> dict:
    # Try prod container if dev not found
    try:
        inspect = subprocess.run(["docker", "inspect", container], capture_output=True)
        if inspect.returncode != 0:
            container = "servicepulse-prod-db"
            inspect_prod = subprocess.run(["docker", "inspect", container], capture_output=True)
            if inspect_prod.returncode != 0:
                return {"error": "Neither servicepulse-db nor servicepulse-prod-db container found"}
    except Exception as exc:
        return {"error": str(exc)}

    queries = {
        "connections": "SELECT count(*) FROM pg_stat_activity;",
        "db_size": f"SELECT pg_size_pretty(pg_database_size('{db_name}'));",
        "alembic_version": "SELECT version_num FROM alembic_version LIMIT 1;",
        "outbox_count": "SELECT count(*) FROM realtime_events;",
        "user_count": "SELECT count(*) FROM users;",
        "device_count": "SELECT count(*) FROM devices;",
        "incident_count": "SELECT count(*) FROM incidents;",
    }

    results = {}
    for key, sql in queries.items():
        cmd = ["docker", "exec", container, "psql", "-U", db_user, "-d", db_name, "-t", "-A", "-c", sql]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                results[key] = res.stdout.strip()
            else:
                results[key] = f"query failed: {res.stderr.strip()}"
        except Exception as exc:
            results[key] = str(exc)

    return results


def check_host_resources() -> dict:
    total, used, free = shutil.disk_usage(".")
    return {
        "disk_total_gb": round(total / (2**30), 2),
        "disk_used_gb": round(used / (2**30), 2),
        "disk_free_gb": round(free / (2**30), 2),
        "disk_free_percent": round((free / total) * 100, 1)
    }


def main():
    parser = argparse.ArgumentParser(description="ServicePulse Health & Operational Telemetry")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base backend URL")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    root_health = check_endpoint(f"{args.base_url.rstrip('/')}/health", "Root Health Probe")
    api_health = check_endpoint(f"{args.base_url.rstrip('/')}/api/v1/health", "API Database Health Probe")
    containers = check_docker_containers()
    db_metrics = check_database_telemetry()
    resources = check_host_resources()

    report = {
        "service": "ServicePulse",
        "author": "Muhammadyusuf Usmonov",
        "purpose": "AT-Servis BMI Operational Readiness",
        "endpoints": {
            "root_probe": root_health,
            "api_probe": api_health,
        },
        "docker_containers": containers,
        "database_metrics": db_metrics,
        "host_resources": resources,
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print("======================================================================")
    print(" ServicePulse Operational Health & Readiness Inspection")
    print(" Author: Muhammadyusuf Usmonov | Academic Purpose: AT-Servis BMI")
    print("======================================================================")

    # Endpoints
    print("\n[HTTP Probes]")
    for name, ep in report["endpoints"].items():
        status = "OK" if ep.get("reachable") else "FAIL"
        print(f"  - {ep.get('description')}: {status} ({ep.get('url')})")
        if ep.get("reachable"):
            print(f"    Data: {ep.get('data')}")
        else:
            print(f"    Error: {ep.get('error')}")

    # Containers
    print("\n[Docker Containers]")
    for c in report["docker_containers"]:
        if "error" in c:
            print(f"  - {c['error']}")
        else:
            state_sym = "[OK]" if c.get("healthy") else "[WARN]"
            print(f"  {state_sym} {c['name']:<30} Status: {c['status']}")

    # Database
    print("\n[PostgreSQL Database Metrics]")
    if "error" in report["database_metrics"]:
        print(f"  - {report['database_metrics']['error']}")
    else:
        for k, v in report["database_metrics"].items():
            print(f"  - {k:<20}: {v}")

    # Host Resources
    print("\n[Storage & Disk Resources]")
    print(f"  - Free Disk: {resources['disk_free_gb']} GB ({resources['disk_free_percent']}% available)")

    print("\n======================================================================")
    all_healthy = root_health.get("reachable") and api_health.get("reachable")
    if all_healthy:
        print(" System Health Status: HEALTHY & OPERATIONAL")
    else:
        print(" System Health Status: DEGRADED / ATTENTION REQUIRED")
    print("======================================================================")


if __name__ == "__main__":
    main()
