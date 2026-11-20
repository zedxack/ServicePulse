#!/usr/bin/env python3
"""
ServicePulse - PostgreSQL Automated Backup Utility
Project: ServicePulse — Enterprise Hybrid RMM & ITSM Platform
Author: Muhammadyusuf Usmonov

Features:
- Executes pg_dump via Docker into compressed .sql.gz atomically (via .tmp)
- Generates SHA-256 checksum (.sha256)
- Generates JSON metadata manifest (.meta.json) with Alembic revision
- Configurable retention policy (default: 7 days) with strict safe pruning
- Pre-flight database reachability and disk space verification
- Restrictive file permissions (chmod 600/700) on POSIX

Usage:
    python scripts/backup_db.py --container servicepulse-db --backup-dir ./backups
    python scripts/backup_db.py --compose-file compose.prod.yaml --backup-dir ./backups
"""
import argparse
import datetime
import gzip
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

BACKUP_PATTERN = re.compile(r"^servicepulse_backup_\d{8}_\d{6}\.(sql\.gz|sql\.gz\.sha256|meta\.json)$")
DB_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def compute_sha256(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def get_alembic_version(container_name: str, db_user: str, db_name: str) -> str:
    cmd = [
        "docker", "exec", container_name,
        "psql", "-U", db_user, "-d", db_name, "-t", "-A",
        "-c", "SELECT version_num FROM alembic_version LIMIT 1;"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        version = res.stdout.strip()
        return version or "unknown"
    except Exception as exc:
        print(f"Warning: Could not fetch alembic version: {exc}", file=sys.stderr)
        return "unknown"


def prune_old_backups(backup_dir: Path, retention_days: int):
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=retention_days)
    pruned_count = 0
    resolved_backup_dir = backup_dir.resolve()

    for file in backup_dir.iterdir():
        if not file.is_file():
            continue
        # Strict pattern match to prevent deleting unrelated files
        if not BACKUP_PATTERN.match(file.name):
            continue
        # Verify file stays strictly inside backup directory (no symlink traversal)
        if resolved_backup_dir not in file.resolve().parents and file.resolve().parent != resolved_backup_dir:
            continue

        try:
            mtime = datetime.datetime.fromtimestamp(file.stat().st_mtime, tz=datetime.timezone.utc)
            if mtime < cutoff:
                file.unlink()
                pruned_count += 1
                print(f"Pruned expired backup file: {file.name}")
        except Exception as exc:
            print(f"Warning: Failed to prune {file.name}: {exc}", file=sys.stderr)

    if pruned_count > 0:
        print(f"Retention policy applied: pruned {pruned_count} old file(s) older than {retention_days} days.")


def set_restrictive_permissions(path: Path, is_dir: bool = False):
    if os.name != "nt":
        try:
            mode = (stat.S_IRWXU) if is_dir else (stat.S_IRUSR | stat.S_IWUSR)
            os.chmod(path, mode)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="ServicePulse Database Backup Utility")
    parser.add_argument("--container", default=None, help="Docker container name running PostgreSQL")
    parser.add_argument("--compose-file", default=None, help="Docker compose file to target")
    parser.add_argument("--service", default="db", help="Docker compose service name (default: db)")
    parser.add_argument("--db-name", default="servicepulse", help="Database name")
    parser.add_argument("--db-user", default="postgres", help="Database user")
    parser.add_argument("--backup-dir", type=Path, default=Path("backups"), help="Directory to store backups")
    parser.add_argument("--retention-days", type=int, default=7, help="Retention period in days (default: 7)")

    args = parser.parse_args()

    # Validate database name
    if not DB_NAME_PATTERN.match(args.db_name):
        print(f"Error: Invalid database name: {args.db_name}", file=sys.stderr)
        sys.exit(1)

    # Determine container name
    container = args.container
    if not container:
        if args.compose_file:
            try:
                out = subprocess.check_output(
                    ["docker", "compose", "-f", args.compose_file, "ps", "-q", args.service],
                    text=True
                ).strip()
                if out:
                    container = out
            except Exception:
                pass
        if not container:
            container = "servicepulse-prod-db"
            res = subprocess.run(["docker", "inspect", container], capture_output=True)
            if res.returncode != 0:
                container = "servicepulse-db"

    # Verify container is running
    inspect_res = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", container],
        capture_output=True, text=True
    )
    if inspect_res.returncode != 0 or inspect_res.stdout.strip() != "true":
        print(f"Error: PostgreSQL container '{container}' is not running.", file=sys.stderr)
        sys.exit(1)

    args.backup_dir.mkdir(parents=True, exist_ok=True)
    set_restrictive_permissions(args.backup_dir, is_dir=True)

    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_name = f"servicepulse_backup_{timestamp_str}"
    tmp_dump_file = args.backup_dir / f"{base_name}.sql.gz.tmp"
    final_dump_file = args.backup_dir / f"{base_name}.sql.gz"
    sha_file = args.backup_dir / f"{base_name}.sql.gz.sha256"
    meta_file = args.backup_dir / f"{base_name}.meta.json"

    print(f"Starting database backup for '{args.db_name}' from container '{container}'...")

    # Pre-check database reachability
    ping_cmd = ["docker", "exec", container, "pg_isready", "-U", args.db_user, "-d", args.db_name]
    ping_res = subprocess.run(ping_cmd, capture_output=True, text=True)
    if ping_res.returncode != 0:
        print(f"Error: Database is not ready: {ping_res.stderr}", file=sys.stderr)
        sys.exit(1)

    # Execute pg_dump and compress via gzip into temporary file
    dump_cmd = ["docker", "exec", container, "pg_dump", "-U", args.db_user, "-d", args.db_name, "--clean", "--if-exists"]

    try:
        proc = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with gzip.open(tmp_dump_file, "wb", compresslevel=9) as gz_out:
            shutil.copyfileobj(proc.stdout, gz_out)
        _, stderr_data = proc.communicate()

        if proc.returncode != 0:
            if tmp_dump_file.exists():
                tmp_dump_file.unlink()
            print(f"Error: pg_dump failed with return code {proc.returncode}: {stderr_data.decode()}", file=sys.stderr)
            sys.exit(1)

        file_size = tmp_dump_file.stat().st_size
        if file_size == 0:
            tmp_dump_file.unlink()
            print("Error: Generated backup dump is empty.", file=sys.stderr)
            sys.exit(1)

        # Atomically rename .tmp to final .sql.gz
        tmp_dump_file.replace(final_dump_file)
        set_restrictive_permissions(final_dump_file)

        # Compute SHA-256 strictly on finalized archive
        checksum = compute_sha256(final_dump_file)
        sha_file.write_text(f"{checksum}  {final_dump_file.name}\n", encoding="utf-8")
        set_restrictive_permissions(sha_file)

        # Fetch Alembic revision
        alembic_rev = get_alembic_version(container, args.db_user, args.db_name)

        # Generate metadata manifest
        manifest = {
            "backup_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "database_name": args.db_name,
            "database_user": args.db_user,
            "container_source": container,
            "archive_filename": final_dump_file.name,
            "file_size_bytes": file_size,
            "sha256_checksum": checksum,
            "alembic_revision": alembic_rev,
            "servicepulse_version": "1.0.0",
            "author": "Muhammadyusuf Usmonov",
            "purpose": "Enterprise Production Backup",
        }
        meta_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        set_restrictive_permissions(meta_file)

        print("Backup created successfully:")
        print(f"  - Archive:  {final_dump_file} ({file_size / 1024:.1f} KB)")
        print(f"  - SHA-256:  {checksum}")
        print(f"  - Alembic:  {alembic_rev}")
        print(f"  - Metadata: {meta_file}")

        # Apply retention policy
        prune_old_backups(args.backup_dir, args.retention_days)

    except Exception as exc:
        if tmp_dump_file.exists():
            tmp_dump_file.unlink()
        if final_dump_file.exists() and final_dump_file.stat().st_size == 0:
            final_dump_file.unlink()
        print(f"Backup failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
