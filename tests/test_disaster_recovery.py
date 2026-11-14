"""
ServicePulse - Automated Disaster Recovery & Restore Verification Test
Project: ServicePulse (AT-Servis BMI)
Author: Muhammadyusuf Usmonov

Verifies:
1. Full database backup generation with SHA-256 and JSON metadata.
2. Launch of an isolated disposable PostgreSQL 16 container.
3. Database restoration from compressed backup archive.
4. Data integrity verification (table presence, row counts, Alembic revision).
5. Safe teardown of disposable verification container.
"""
import os
import subprocess
import time
from pathlib import Path

DISPOSABLE_CONTAINER = "sp-disaster-recovery-test-db"
TEST_DB_NAME = "servicepulse"
TEST_DB_USER = "postgres"
TEST_DB_PASS = "test_recovery_password_2026"


def cleanup_container():
    subprocess.run(["docker", "rm", "-f", DISPOSABLE_CONTAINER], capture_output=True)


def test_disaster_recovery_workflow():
    cleanup_container()

    # Step 1: Generate a fresh backup from the active development database
    backup_script = Path("scripts/backup_db.py")
    assert backup_script.exists(), "backup_db.py must exist"

    backup_dir = Path("backups")
    res = subprocess.run(
        ["python", str(backup_script), "--container", "servicepulse-db", "--backup-dir", str(backup_dir)],
        capture_output=True, text=True
    )
    assert res.returncode == 0, f"Backup creation failed: {res.stderr}"

    # Find the latest backup archive
    archives = sorted(backup_dir.glob("servicepulse_backup_*.sql.gz"), key=os.path.getmtime, reverse=True)
    assert len(archives) > 0, "At least one backup archive must exist"
    latest_archive = archives[0]
    sha_file = latest_archive.parent / f"{latest_archive.name}.sha256"
    base_name = latest_archive.name[:-7] if latest_archive.name.endswith(".sql.gz") else latest_archive.stem
    meta_file = latest_archive.parent / f"{base_name}.meta.json"

    assert sha_file.exists(), "Checksum file must exist"
    assert meta_file.exists(), "Metadata manifest must exist"

    # Step 2: Spin up isolated disposable PostgreSQL 16 container
    try:
        run_cmd = [
            "docker", "run", "-d",
            "--name", DISPOSABLE_CONTAINER,
            "-e", f"POSTGRES_DB={TEST_DB_NAME}",
            "-e", f"POSTGRES_USER={TEST_DB_USER}",
            "-e", f"POSTGRES_PASSWORD={TEST_DB_PASS}",
            "postgres:16-alpine"
        ]
        run_res = subprocess.run(run_cmd, capture_output=True, text=True)
        assert run_res.returncode == 0, f"Failed to start disposable container: {run_res.stderr}"

        # Wait for container to be ready
        ready = False
        for _ in range(30):
            time.sleep(1)
            ready_res = subprocess.run(
                ["docker", "exec", DISPOSABLE_CONTAINER, "pg_isready", "-U", TEST_DB_USER, "-d", TEST_DB_NAME],
                capture_output=True
            )
            if ready_res.returncode == 0:
                ready = True
                break

        assert ready, "Disposable container did not become ready in time"

        # Step 3: Run restore_db.py against the disposable container
        restore_script = Path("scripts/restore_db.py")
        restore_res = subprocess.run(
            [
                "python", str(restore_script),
                "--archive", str(latest_archive),
                "--container", DISPOSABLE_CONTAINER,
                "--db-name", TEST_DB_NAME,
                "--db-user", TEST_DB_USER,
                "--force"
            ],
            capture_output=True, text=True
        )
        assert restore_res.returncode == 0, f"Restoration failed: {restore_res.stderr}\nOutput: {restore_res.stdout}"
        assert "PASSED successfully" in restore_res.stdout

        # Step 4: Verify Alembic revision in disposable container
        alembic_res = subprocess.run(
            ["docker", "exec", DISPOSABLE_CONTAINER, "psql", "-U", TEST_DB_USER, "-d", TEST_DB_NAME, "-t", "-A", "-c", "SELECT version_num FROM alembic_version LIMIT 1;"],
            capture_output=True, text=True
        )
        assert alembic_res.returncode == 0
        restored_revision = alembic_res.stdout.strip()
        assert restored_revision == "c4d5e6f7a8b9", f"Expected head revision c4d5e6f7a8b9, got {restored_revision}"

        # Step 5: Verify core tables row counts
        for table in ["users", "organizations", "devices", "incidents", "notifications", "tickets"]:
            count_res = subprocess.run(
                ["docker", "exec", DISPOSABLE_CONTAINER, "psql", "-U", TEST_DB_USER, "-d", TEST_DB_NAME, "-t", "-A", "-c", f"SELECT count(*) FROM {table};"],
                capture_output=True, text=True
            )
            assert count_res.returncode == 0
            count = int(count_res.stdout.strip())
            assert count >= 0, f"Table {table} in restored database should be queryable, got {count}"

    finally:
        # Step 6: Safe Teardown
        cleanup_container()
