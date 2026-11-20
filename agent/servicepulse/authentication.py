"""
ServicePulse Native Windows Agent - DPAPI Protected Credential Storage
Secures Agent credentials using Windows Data Protection API (CryptProtectData).
Author: Muhammadyusuf Usmonov
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from servicepulse.logging.setup import get_logger

logger = get_logger()

# Check if native Windows DPAPI is available
_HAS_WIN32CRYPT = False
if sys.platform == "win32":
    try:
        import win32crypt
        _HAS_WIN32CRYPT = True
    except ImportError:
        _HAS_WIN32CRYPT = False

# Windows DPAPI Flag Constants
CRYPTPROTECT_DEFAULT = 0x0             # Default user-scope (MasterKey in %APPDATA%\Microsoft\Protect\{SID})
CRYPTPROTECT_UI_FORBIDDEN = 0x1        # Disallow UI prompt (remains user-scope when 0x4 is omitted)
CRYPTPROTECT_LOCAL_MACHINE = 0x4       # Machine-scope: binds to machine LSA secret in %SystemRoot%\System32\Microsoft\Protect
# Combined machine-scope + UI forbidden (dwFlags = 0x5)
DPAPI_MACHINE_FLAGS = CRYPTPROTECT_UI_FORBIDDEN | CRYPTPROTECT_LOCAL_MACHINE  # 0x5


def get_current_user_sid() -> Optional[str]:
    """
    Retrieve the current Windows security principal SID.
    Prefers native win32security token inspection, with whoami fallback.
    """
    if sys.platform != "win32":
        return None
    try:
        import ntsecuritycon
        import win32api
        import win32security
        tok = win32security.OpenProcessToken(win32api.GetCurrentProcess(), ntsecuritycon.TOKEN_QUERY)
        user_sid, _ = win32security.GetTokenInformation(tok, ntsecuritycon.TokenUser)
        return win32security.ConvertSidToStringSid(user_sid)
    except Exception:
        pass
    try:
        import csv
        import io
        import subprocess
        res = subprocess.run(
            ["whoami.exe", "/user", "/fo", "csv"],
            capture_output=True,
            text=True,
            errors="replace",
            check=False
        )
        if res.returncode == 0 and res.stdout:
            rows = list(csv.reader(io.StringIO(res.stdout.strip())))
            if len(rows) >= 2 and len(rows[1]) >= 2:
                return rows[1][1].strip()
    except Exception:
        pass
    return None


def _apply_restrictive_acls(target_path: Path, is_directory: bool = False) -> None:
    """
    Apply strict NTFS DACLs on sensitive agent files or directories.
    Grants FullControl to SYSTEM (S-1-5-18), BUILTIN\\Administrators (S-1-5-32-544),
    and the current executing user's specific SID.
    Strips inheritance (/inheritance:r) to completely deny BUILTIN\\Users (S-1-5-32-545) and Everyone.
    """
    if sys.platform != "win32" or not target_path.exists():
        return

    import subprocess
    user_sid = get_current_user_sid()
    inherit_flags = "(OI)(CI)(F)" if is_directory else "(F)"
    grants = [
        "/inheritance:r",
        "/grant:r",
        f"*S-1-5-18:{inherit_flags}",
        f"*S-1-5-32-544:{inherit_flags}",
    ]
    if user_sid:
        grants.append(f"*{user_sid}:{inherit_flags}")
    else:
        user = os.environ.get("USERNAME")
        if user:
            grants.append(f"{user}:{inherit_flags}")

    try:
        subprocess.run(
            ["icacls.exe", str(target_path)] + grants,
            capture_output=True,
            check=False,
            timeout=5
        )
    except Exception as e:
        logger.debug(f"Could not apply restrictive NTFS ACLs on {target_path}: {e}")

    try:
        os.chmod(target_path, 0o700 if is_directory else 0o600)
    except Exception:
        pass


class AgentCredentials(BaseModel):
    """Securely loaded credentials for authenticated communication."""
    agent_uuid: str
    api_token: str
    device_id: Optional[int] = None
    organization_id: Optional[int] = None


class CredentialStore:
    """
    Protects and retrieves agent credentials using Windows DPAPI.
    The encrypted payload is bound to the local machine and executing security context.
    """

    def __init__(self, credentials_path: Path):
        self.path = credentials_path

    def _encrypt_bytes(self, plaintext: bytes) -> bytes:
        """
        Encrypt byte sequence with Windows DPAPI using machine scope.
        dwFlags = 0x5 combines CRYPTPROTECT_UI_FORBIDDEN (0x1) and CRYPTPROTECT_LOCAL_MACHINE (0x4).
        By default, CryptProtectData uses user-scope (0x0).
        Adding CRYPTPROTECT_LOCAL_MACHINE (0x4) enables both the enrolling administrator
        and the background Windows Service (running under NT AUTHORITY\\SYSTEM) to decrypt
        the persisted credential across restarts, while DPAPI prevents off-machine decryption.
        Local access isolation is enforced by NTFS ACLs.
        """
        if _HAS_WIN32CRYPT:
            return win32crypt.CryptProtectData(
                plaintext,
                "ServicePulse Agent Credentials",
                None,
                None,
                None,
                DPAPI_MACHINE_FLAGS
            )
        else:
            # Fallback for mock/test environments
            logger.warning("Windows DPAPI not available; using fallback encryption for testing environment")
            key = b"ServicePulseTestKey"
            enc = bytes(b ^ key[i % len(key)] for i, b in enumerate(plaintext))
            return b"SP_TEST_MOCK:" + enc

    def _decrypt_bytes(self, ciphertext: bytes) -> bytes:
        """Decrypt byte sequence with Windows DPAPI."""
        if _HAS_WIN32CRYPT and not ciphertext.startswith(b"SP_TEST_MOCK:"):
            # win32crypt.CryptUnprotectData returns (description, decrypted_bytes)
            # dwFlags = 0x1 (CRYPTPROTECT_UI_FORBIDDEN) disables any UI prompt during decryption
            _, decrypted = win32crypt.CryptUnprotectData(
                ciphertext,
                None,
                None,
                None,
                CRYPTPROTECT_UI_FORBIDDEN
            )
            return decrypted
        elif ciphertext.startswith(b"SP_TEST_MOCK:"):
            raw = ciphertext[len(b"SP_TEST_MOCK:"):]
            key = b"ServicePulseTestKey"
            return bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
        else:
            raise RuntimeError("Cannot decrypt credentials: DPAPI unavailable and payload is not a mock format")

    def save_credentials(self, creds: AgentCredentials) -> None:
        """Encrypt and persist credentials to protected file."""
        parent_dir = self.path.parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        # Secure parent directory if on Windows
        if sys.platform == "win32":
            _apply_restrictive_acls(parent_dir, is_directory=True)

        payload = creds.model_dump_json().encode("utf-8")
        encrypted = self._encrypt_bytes(payload)

        # Write atomically via temp file
        temp_path = self.path.with_suffix(".tmp")
        try:
            with open(temp_path, "wb") as f:
                f.write(encrypted)

            # Apply restrictive ACLs on temp file before moving
            if sys.platform == "win32":
                _apply_restrictive_acls(temp_path, is_directory=False)

            temp_path.replace(self.path)

            # Re-assert restrictive ACLs on final file to guarantee strict DACL
            if sys.platform == "win32":
                _apply_restrictive_acls(self.path, is_directory=False)

            logger.info(f"Credentials securely stored to {self.path} (DPAPI machine-scope: {_HAS_WIN32CRYPT})")
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    def load_credentials(self) -> Optional[AgentCredentials]:
        """Decrypt and load credentials from disk."""
        if not self.path.is_file():
            return None

        try:
            with open(self.path, "rb") as f:
                ciphertext = f.read()

            if not ciphertext:
                return None

            plaintext = self._decrypt_bytes(ciphertext)
            data = json.loads(plaintext.decode("utf-8"))
            return AgentCredentials(**data)
        except Exception as e:
            logger.error(f"Failed to load or decrypt credentials from {self.path}: {e}")
            return None

    def clear_credentials(self) -> None:
        """Remove stored credentials file."""
        if self.path.is_file():
            try:
                self.path.unlink()
                logger.info(f"Cleared credentials file at {self.path}")
            except Exception as e:
                logger.error(f"Failed to remove credentials file {self.path}: {e}")

    def has_credentials(self) -> bool:
        """Check whether valid credentials file exists."""
        return self.path.is_file() and self.path.stat().st_size > 0
