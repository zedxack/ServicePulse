"""
ServicePulse - Security and Authentication Module
Argon2id password hashing & PyJWT token handling
Author: Muhammadyusuf Usmonov
"""
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from backend.app.core.config import settings

# Argon2id password hasher with secure enterprise parameters
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16
)


def hash_password(password: str) -> str:
    """Hash password using Argon2id algorithm."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2id hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Check if password hash needs rehash due to upgraded parameters."""
    return ph.check_needs_rehash(hashed_password)


def create_access_token(
    subject: str,
    claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generate signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "access"
    }
    if claims:
        payload.update(claims)

    encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None
) -> str:
    """Generate signed JWT refresh token with unique jti identifier."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "refresh",
        "jti": jti or uuid.uuid4().hex
    }

    encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT token."""
    try:
        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return decoded
    except jwt.PyJWTError as exc:
        raise ValueError(f"Invalid token: {str(exc)}") from exc


SENSITIVE_PATTERNS = [
    # Bearer tokens
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), r"\1[REDACTED]"),
    # Authorization header
    (re.compile(r"(?i)(authorization:\s*)[^\r\n]+"), r"\1[REDACTED]"),
    # Passwords and secrets in key-value format
    (
        re.compile(
            r"(?i)\b(password|secret|token|api[_-]?key|enrollment_secret|client_secret)\b(\s*[:=]\s*['\"]?)[^\s'\",;]+(['\"]?)"
        ),
        r"\1\2[REDACTED]\3",
    ),
    # Long base64/hex blobs (64+ chars)
    (re.compile(r"\b[A-Za-z0-9+/]{64,}={0,2}\b"), "[REDACTED_BLOB]"),
]


def redact_sensitive_text(text: Optional[str]) -> Optional[str]:
    """Redact sensitive credentials, tokens, secrets and authorization headers from text."""
    if not text:
        return text
    redacted = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted

