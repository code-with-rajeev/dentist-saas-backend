"""
Unit tests for app/core/security.py — JWT create/decode + password hashing.
These are pure Python unit tests (no DB, no HTTP client needed).
"""

# Standard library
from datetime import timedelta

# Third-party
import pytest

# Internal
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("secret123")
        assert hashed != "secret123"

    def test_verify_correct_password(self):
        hashed = hash_password("MyPass123")
        assert verify_password("MyPass123", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("MyPass123")
        assert verify_password("WrongPass", hashed) is False

    def test_same_password_produces_different_hashes(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        # bcrypt salts are random per call
        assert h1 != h2

    def test_verify_still_works_across_hashes(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert verify_password("same_password", h1)
        assert verify_password("same_password", h2)


class TestJWTTokens:
    def test_create_and_decode_access_token(self):
        payload = {"sub": "user-id-123", "clinic_id": "clinic-abc"}
        token = create_access_token(data=payload)
        decoded = decode_token(token)
        assert decoded["sub"] == "user-id-123"
        assert decoded["type"] == "access"

    def test_create_and_decode_refresh_token(self):
        token = create_refresh_token(data={"sub": "user-abc"})
        decoded = decode_token(token)
        assert decoded["sub"] == "user-abc"
        assert decoded["type"] == "refresh"

    def test_access_token_has_correct_type(self):
        token = create_access_token(data={"sub": "x"})
        decoded = decode_token(token)
        assert decoded["type"] == "access"

    def test_invalid_token_string_raises(self):
        with pytest.raises(Exception):
            decode_token("not.a.valid.jwt.token")
