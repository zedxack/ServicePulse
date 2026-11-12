"""
ServicePulse - Security, Argon2id & JWT Tests
Author: Muhammadyusuf Usmonov
"""
from datetime import timedelta

import pytest

from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_argon2id_password_hashing():
    """Verify Argon2id password hashing and comparison."""
    password = "SecureSuperPassword2026!"
    hashed = hash_password(password)

    # Hash should start with $argon2id$
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_access_token_creation_and_decoding():
    """Verify JWT access token creation and decoding."""
    subject = "user-123"
    claims = {"role": "admin", "full_name": "Muhammadyusuf Usmonov"}
    token = create_access_token(subject, claims=claims)

    decoded = decode_token(token)
    assert decoded["sub"] == subject
    assert decoded["role"] == "admin"
    assert decoded["full_name"] == "Muhammadyusuf Usmonov"
    assert decoded["type"] == "access"


def test_jwt_expired_token():
    """Verify expired token raises validation error."""
    subject = "user-expired"
    token = create_access_token(subject, expires_delta=timedelta(seconds=-10))

    with pytest.raises(ValueError, match="Invalid token"):
        decode_token(token)


def test_jwt_refresh_token_creation():
    """Verify refresh token has proper type."""
    subject = "user-456"
    token = create_refresh_token(subject)
    decoded = decode_token(token)
    assert decoded["sub"] == subject
    assert decoded["type"] == "refresh"
