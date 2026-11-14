#!/usr/bin/env python3
"""
ServicePulse - PostgreSQL Disaster Recovery & Restoration Utility
Project: ServicePulse (AT-Servis BMI)
Author: Muhammadyusuf Usmonov

Safety Guardrails:
- Explicit target container requirement (no default fallback to live DB)
- Production container protection (requires --confirm-production)
- Pre-restoration SHA-256 integrity and metadata verification
- Strict input validation against shell/SQL injection
- Aborts immediately on restore or verification errors
- Zero credential leakage

Usage:
    python scripts/restore_db.py --archive backups/servicepulse_backup_YYYYMMDD_HHMMSS.sql.gz --verify-only
    python scripts/restore_db.py --archive backups/servicepulse_backup_YYYYMMDD_HHMMSS.sql.gz --container sp-test-db --force
    python scripts/restore_db.py --archive backups/servicepulse_backup_YYYYMMDD_HHMMSS.sql.gz --container servicepulse-prod-db --confirm-production
"""
import argparse
import gzip
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

DB_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
CONTAINER_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+$")


def compute_sha256(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def verify_integrity(archive_path: Path) -> tuple[bool, dict]:
    if not archive_path.exists():
        print(f"Error: Archive not found: {archive_path}", file=sys.stderr)
        return False, {}

    sha_path = archive_path.parent / f"{archive_path.name}.sha256"
    base_name = archive_path.name[:-7] if archive_path.name.endswith(".sql.gz") else archive_path.stem
    meta_path = archive_path.parent / f"{base_name}.meta.json"

    expected_sha = None
    manifest = {}

    if meta_path.exists():
        try:
            manifest = json.loads(meta_path.read_text(encoding="utf-8"))
            expected_sha = manifest.get("sha256_checksum")
        except Exception as exc:
            print(f"Warning: Could not read metadata manifest: {exc}", file=sys.stderr)

    if not expected_sha and sha_path.exists():
        first_line = sha_path.read_text(encoding="utf-8").strip().split()
        if first_line:
            expected_sha = first_line[0]

    actual_sha = compute_sha256(archive_path)

    if expected_sha:
        if actual_sha.lower() != expected_sha.lower():
            print("Error: SHA-256 checksum MISMATCH!", file=sys.stderr)
            print(f"  Expected: {expected_sha}", file=sys.stderr)
            print(f"  Actual:   {actual_sha}", file=sys.stderr)
            return False, manifest
        print(f"SHA-256 integrity verified successfully: {actual_sha}")
    else:
        print(f"Warning: No checksum file found. Computed SHA-256: {actual_sha}")

    # Verify gzip archive format
    try:
        with gzip.open(archive_path, "rb") as f:
            chunk = f.read(1024)
            if not chunk:
                print("Error: Archive is empty.", file=sys.stderr)
                return False, manifest
    except Exception as exc:
        print(f"Error: Gzip archive is corrupt: {exc}", file=sys.stderr)
        return False, manifest

    return True, manifest


def verify_restored_database(container: str, db_user: str, db_name: str, expected_manifest: dict) -> bool:
    print("\nVerifying restored database integrity...")

    # Check tables
    check_tables_sql = """
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name;
    """
    res = subprocess.run(
        ["docker", "exec", container, "psql", "-U", db_user, "-d", db_name, "-t", "-A", "-c", check_tables_sql],
        capture_output=True, text=True
    )
    if res.returncode != 0:
        print(f"Error checking tables: {res.stderr}", file=sys.stderr)
        return False

    tables = [t.strip() for t in res.stdout.strip().split("\n") if t.strip()]
    expected_tables = ["users", "organizations", "devices", "incidents", "tickets", "notifications", "realtime_events", "alembic_version"]
    missing = [tbl for tbl in expected_tables if tbl not in tables]

    if missing:
        print(f"Error: Missing required tables in restored database: {missing}", file=sys.stderr)
        return False

    print(f"All {len(expected_tables)} critical tables verified present in restored database.")

    # Check Alembic version
    alembic_res = subprocess.run(
        ["docker", "exec", container, "psql", "-U", db_user, "-d", db_name, "-t", "-A", "-c", "SELECT version_num FROM alembic_version LIMIT 1;"],
        capture_output=True, text=True
    )
    alembic_rev = alembic_res.stdout.strip() if alembic_res.returncode == 0 else ""
    if not alembic_rev:
        print("Error: Alembic revision table is missing or empty in restored database.", file=sys.stderr)
        return False

    print(f"Alembic database revision: {alembic_rev}")

    expected_rev = expected_manifest.get("alembic_revision")
    if expected_rev and expected_rev != "unknown":
        if alembic_rev != expected_rev:
            print(f"Error: Restored Alembic revision ({alembic_rev}) does not match manifest ({expected_rev})", file=sys.stderr)
            return False

    # Check user count
    user_res = subprocess.run(
        ["docker", "exec", container, "psql", "-U", db_user, "-d", db_name, "-t", "-A", "-c", "SELECT count(*) FROM users;"],
        capture_output=True, text=True
    )
    user_count = user_res.stdout.strip() if user_res.returncode == 0 else "0"
    print(f"User accounts verified: {user_count}")

    # Check organization count
    org_res = subprocess.run(
        ["docker", "exec", container, "psql", "-U", db_user, "-d", db_name, "-t", "-A", "-c", "SELECT count(*) FROM organizations;"],
        capture_output=True, text=True
    )
    org_count = org_res.stdout.strip() if org_res.returncode == 0 else "0"
    print(f"Organizations verified: {org_count}")

    return True


def main():
    parser = argparse.ArgumentParser(description="ServicePulse Database Restoration Utility")
    parser.add_argument("--archive", required=True, type=Path, help="Path to .sql.gz backup archive")
    parser.add_argument("--container", default=None, help="Target Docker container name running PostgreSQL (MANDATORY for restore)")
    parser.add_argument("--db-name", default="servicepulse", help="Target database name")
    parser.add_argument("--db-user", default="postgres", help="Target database user")
    parser.add_argument("--verify-only", action="store_true", help="Only verify archive integrity without restoring")
    parser.add_argument("--confirm-production", action="store_true", help="Explicit acknowledgement required when targeting a production container")
    parser.add_argument("--force", action="store_true", help="Bypass interactive confirmation prompt")

    args = parser.parse_args()

    # Step 1: Integrity Verification
    valid, manifest = verify_integrity(args.archive)
    if not valid:
        print("Restoration aborted: Archive integrity check failed.", file=sys.stderr)
        sys.exit(1)

    if args.verify_only:
        print("Verification completed successfully. Archive and manifest are valid.")
        sys.exit(0)

    # Step 2: Strict Safety Checks on Target Container
    if not args.container:
        print("Error: Target container must be explicitly specified via --container.", file=sys.stderr)
        print("Automatic defaulting to live database containers is disabled to prevent accidental data loss.", file=sys.stderr)
        sys.exit(2)

    container = args.container.strip()
    if not CONTAINER_NAME_PATTERN.match(container):
        print(f"Error: Invalid container name format: '{container}'", file=sys.stderr)
        sys.exit(2)

    if not DB_NAME_PATTERN.match(args.db_name):
        print(f"Error: Invalid database name format: '{args.db_name}'", file=sys.stderr)
        sys.exit(2)

    # Production Container Protection (Checked prior to execution to prevent unauthorized attempts)
    is_production = "prod" in container.lower()
    if is_production and not args.confirm_production:
        print(f"CRITICAL SAFETY GUARD: Container '{container}' appears to be a PRODUCTION database.", file=sys.stderr)
        print("To confirm restoration to production, you MUST explicitly provide --confirm-production.", file=sys.stderr)
        sys.exit(2)

    # Verify target container is running
    inspect_res = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", container],
        capture_output=True, text=True
    )
    if inspect_res.returncode != 0 or inspect_res.stdout.strip() != "true":
        print(f"Error: Target container '{container}' is not running.", file=sys.stderr)
        sys.exit(1)

    if not args.force:
        print(f"\nCAUTION: You are about to restore {args.archive.name} into database '{args.db_name}' on container '{container}'.")
        print("Existing data in the target database will be overwritten.")
        confirm = input("Type 'RESTORE' to proceed: ").strip()
        if confirm != "RESTORE":
            print("Restoration cancelled by user.")
            sys.exit(0)

    print(f"Restoring database from '{args.archive.name}' into container '{container}'...")

    # Terminate active connections to the explicitly specified database only
    terminate_sql = f"""
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = '{args.db_name}' AND pid <> pg_backend_pid();
    """
    subprocess.run(
        ["docker", "exec", container, "psql", "-U", args.db_user, "-d", "postgres", "-c", terminate_sql],
        capture_output=True
    )

    # Decompress and pipe directly into psql
    restore_cmd = ["docker", "exec", "-i", container, "psql", "-U", args.db_user, "-d", args.db_name]

    try:
        proc = subprocess.Popen(restore_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with gzip.open(args.archive, "rb") as gz_in:
            while chunk := gz_in.read(65536):
                proc.stdin.write(chunk)
        stdout_data, stderr_data = proc.communicate()

        if proc.returncode != 0:
            print(f"Error: psql exited with failure code {proc.returncode}: {stderr_data.decode()}", file=sys.stderr)
            sys.exit(1)

        print("Database stream restoration finished.")

        # Post-restore verification
        if not verify_restored_database(container, args.db_user, args.db_name, manifest):
            print("\nError: Post-restore database integrity verification FAILED.", file=sys.stderr)
            sys.exit(1)

        print("\nDatabase restoration and verification PASSED successfully.")

    except Exception as exc:
        print(f"Error during restoration: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
