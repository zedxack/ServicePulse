#!/usr/bin/env python3
"""
ServicePulse - Production Secrets Generator & Validator
Project: ServicePulse (AT-Servis BMI)
Author: Muhammadyusuf Usmonov

Generates cryptographically secure secrets for production deployment:
- JWT signing SECRET_KEY (64-char hex)
- AGENT_ENROLLMENT_SECRET (44-char urlsafe)
- POSTGRES_PASSWORD (32-char secure alphanumeric)
- Initial admin credentials (superadmin, support, employee)

Usage:
    python scripts/generate_secrets.py --print
    python scripts/generate_secrets.py --write .env.production
    python scripts/generate_secrets.py --check .env.production
"""
import argparse
import os
import re
import secrets
import stat
import string
import sys
from pathlib import Path


def generate_alphanumeric_password(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    # Ensure at least one lowercase, uppercase, digit, and symbol
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*()-_=+" for c in pwd)
        ):
            return pwd


def generate_all_secrets() -> dict:
    return {
        "SECRET_KEY": secrets.token_hex(32),
        "AGENT_ENROLLMENT_SECRET": secrets.token_urlsafe(32),
        "POSTGRES_PASSWORD": generate_alphanumeric_password(32),
        "FIRST_SUPERUSER_PASSWORD": generate_alphanumeric_password(24),
        "FIRST_SUPPORT_PASSWORD": generate_alphanumeric_password(24),
        "FIRST_EMPLOYEE_PASSWORD": generate_alphanumeric_password(24),
    }


def write_env_file(template_path: Path, output_path: Path, secrets_dict: dict):
    if not template_path.exists():
        print(f"Error: Template file not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    template_content = template_path.read_text(encoding="utf-8")

    replacements = {
        "REPLACE_WITH_STRONG_RANDOM_64_CHAR_HEX_SECRET_KEY_FOR_PRODUCTION": secrets_dict["SECRET_KEY"],
        "REPLACE_WITH_STRONG_RANDOM_AGENT_ENROLLMENT_SECRET_32_CHARS": secrets_dict["AGENT_ENROLLMENT_SECRET"],
        "REPLACE_WITH_STRONG_RANDOM_DATABASE_PASSWORD": secrets_dict["POSTGRES_PASSWORD"],
        "REPLACE_WITH_STRONG_INITIAL_ADMIN_PASSWORD": secrets_dict["FIRST_SUPERUSER_PASSWORD"],
        "REPLACE_WITH_STRONG_INITIAL_SUPPORT_PASSWORD": secrets_dict["FIRST_SUPPORT_PASSWORD"],
        "REPLACE_WITH_STRONG_INITIAL_EMPLOYEE_PASSWORD": secrets_dict["FIRST_EMPLOYEE_PASSWORD"],
    }

    content = template_content
    for placeholder, val in replacements.items():
        content = content.replace(placeholder, val)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    # Set file permissions to chmod 600 (owner read/write only) on POSIX
    try:
        if os.name != "nt":
            os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception as exc:
        print(f"Warning: Could not set restrictive file permissions: {exc}", file=sys.stderr)

    print(f"Successfully generated production environment file: {output_path}")
    print("Security reminder: Ensure file permissions are set to chmod 600 and never commit to Git.")


def check_env_file(env_path: Path) -> bool:
    if not env_path.exists():
        print(f"Error: File not found: {env_path}", file=sys.stderr)
        return False

    content = env_path.read_text(encoding="utf-8")
    errors = []

    # Check SECRET_KEY
    sk_match = re.search(r'^\s*SECRET_KEY\s*=\s*["\']?([^"\'\r\n]+)["\']?', content, re.MULTILINE)
    if not sk_match:
        errors.append("SECRET_KEY is missing")
    else:
        sk = sk_match.group(1).strip()
        if "REPLACE" in sk or "insecure" in sk or len(sk) < 32:
            errors.append(f"SECRET_KEY is insecure or placeholder (length: {len(sk)})")

    # Check AGENT_ENROLLMENT_SECRET
    aes_match = re.search(r'^\s*AGENT_ENROLLMENT_SECRET\s*=\s*["\']?([^"\'\r\n]+)["\']?', content, re.MULTILINE)
    if not aes_match:
        errors.append("AGENT_ENROLLMENT_SECRET is missing")
    else:
        aes = aes_match.group(1).strip()
        if "REPLACE" in aes or "enrollment-secret-2026" in aes or len(aes) < 32:
            errors.append(f"AGENT_ENROLLMENT_SECRET is insecure or placeholder (length: {len(aes)})")

    # Check POSTGRES_PASSWORD
    pg_match = re.search(r'^\s*POSTGRES_PASSWORD\s*=\s*["\']?([^"\'\r\n]+)["\']?', content, re.MULTILINE)
    if not pg_match:
        errors.append("POSTGRES_PASSWORD is missing")
    else:
        pg = pg_match.group(1).strip()
        if "REPLACE" in pg or len(pg) < 16:
            errors.append(f"POSTGRES_PASSWORD is insecure or placeholder (length: {len(pg)})")

    # Check DEBUG
    dbg_match = re.search(r'^\s*DEBUG\s*=\s*["\']?([^"\'\r\n]+)["\']?', content, re.MULTILINE)
    if dbg_match and dbg_match.group(1).strip().lower() in ("true", "1", "yes"):
        errors.append("DEBUG is set to true; production requires DEBUG=false")

    if errors:
        print(f"Validation FAILED for {env_path}:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return False
    else:
        print(f"Validation PASSED for {env_path}: All critical production secrets meet security requirements.")
        return True


def main():
    parser = argparse.ArgumentParser(description="ServicePulse Production Secrets Generator")
    parser.add_argument("--print", action="store_true", help="Print generated secrets to stdout")
    parser.add_argument("--write", type=Path, help="Write secrets into target env file using template")
    parser.add_argument("--template", type=Path, default=Path("infra/env/.env.production.template"), help="Path to template")
    parser.add_argument("--check", type=Path, help="Validate an existing env file against production security standards")

    args = parser.parse_args()

    if args.check:
        success = check_env_file(args.check)
        sys.exit(0 if success else 1)

    secrets_dict = generate_all_secrets()

    if args.print or (not args.write and not args.check):
        print("Generated ServicePulse Production Secrets:")
        print("=" * 60)
        for k, v in secrets_dict.items():
            print(f"{k}={v}")
        print("=" * 60)

    if args.write:
        write_env_file(args.template, args.write, secrets_dict)


if __name__ == "__main__":
    main()
