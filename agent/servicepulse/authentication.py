"""
ServicePulse Native Windows Agent - DPAPI Protected Credential Storage
Secures Agent credentials using Windows Data Protection API (CryptProtectData).
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
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
        """Encrypt byte sequence with Windows DPAPI (machine or user scope)."""
        if _HAS_WIN32CRYPT:
            # CryptProtectData(data, description, optional_entropy, reserved, prompt_struct, flags)
            # CRYPTPROTECT_UI_FORBIDDEN = 0x1
            return win32crypt.CryptProtectData(
                plaintext,
                "ServicePulse Agent Credentials",
                None,
                None,
                None,
                0x1
            )
        else:
            # Fallback for mock/test environments
            logger.warning("Windows DPAPI not available; using fallback encryption for testing environment")
            # Simple XOR-based wrapper with header for testing non-Windows environments
            key = b"ServicePulseTestKey"
            enc = bytes(b ^ key[i % len(key)] for i, b in enumerate(plaintext))
            return b"SP_TEST_MOCK:" + enc

    def _decrypt_bytes(self, ciphertext: bytes) -> bytes:
        """Decrypt byte sequence with Windows DPAPI."""
        if _HAS_WIN32CRYPT and not ciphertext.startswith(b"SP_TEST_MOCK:"):
            # win32crypt.CryptUnprotectData returns (description, decrypted_bytes)
            _, decrypted = win32crypt.CryptUnprotectData(
                ciphertext,
                None,
                None,
                None,
                0x1
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
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = creds.model_dump_json().encode("utf-8")
        encrypted = self._encrypt_bytes(payload)

        # Write atomically via temp file
        temp_path = self.path.with_suffix(".tmp")
        with open(temp_path, "wb") as f:
            f.write(encrypted)

        # On Windows, set restricted file permissions if possible
        if sys.platform == "win32":
            try:
                # Grant access only to current user and SYSTEM
                os.chmod(temp_path, 0o600)
            except Exception:
                pass

        temp_path.replace(self.path)
        logger.info(f"Credentials securely stored to {self.path} (DPAPI encrypted: {_HAS_WIN32CRYPT})")

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
