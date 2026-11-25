import base64
import hashlib
import hmac
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt

from app.core.config import settings

# Scrypt parameters (OWASP-aligned memory-hard KDF via Python stdlib OpenSSL)
SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32


def hash_password(password: str) -> str:
    """Hash password using memory-hard scrypt with cryptographically random 16-byte salt."""
    salt = os.urandom(16)
    dk = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    salt_b64 = base64.b64encode(salt).decode("utf-8")
    dk_b64 = base64.b64encode(dk).decode("utf-8")
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt_b64}${dk_b64}"


def needs_rehash(hashed_password: str) -> bool:
    """Returns True if the stored password uses a legacy format (e.g., PBKDF2) instead of current scrypt."""
    return not hashed_password.startswith("scrypt$")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against scrypt or legacy PBKDF2-HMAC-SHA256 hash using constant-time comparison."""
    try:
        if hashed_password.startswith("scrypt$"):
            parts = hashed_password.split("$")
            if len(parts) != 6:
                return False
            _, n_str, r_str, p_str, salt_b64, hash_b64 = parts
            salt = base64.b64decode(salt_b64)
            expected_dk = base64.b64decode(hash_b64)
            actual_dk = hashlib.scrypt(
                plain_password.encode("utf-8"),
                salt=salt,
                n=int(n_str),
                r=int(r_str),
                p=int(p_str),
                dklen=len(expected_dk),
            )
            return hmac.compare_digest(expected_dk, actual_dk)

        # Legacy PBKDF2-HMAC-SHA256 verification (100,000 rounds) for existing accounts
        salt_b64, hash_b64 = hashed_password.split("$")
        salt = base64.b64decode(salt_b64)
        expected_dk = base64.b64decode(hash_b64)
        actual_dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(expected_dk, actual_dk)
    except Exception:
        return False


def validate_password_strength(password: str) -> Optional[str]:
    """Returns an error message if password does not meet minimum policy, else None."""
    if not password or len(password) < 8:
        return "Password must be at least 8 characters long."
    if len(password) > 128:
        return "Password must not exceed 128 characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password):
        return "Password must contain both letters and numbers."
    return None


def _build_token(
    data: dict[str, Any],
    token_type: str,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(timezone.utc)
    to_encode = data.copy()
    to_encode.update({
        "exp": now + expires_delta,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": token_type,
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _build_token(data, token_type="access", expires_delta=delta)


def create_refresh_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    delta = expires_delta or timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    return _build_token(data, token_type="refresh", expires_delta=delta)


def decode_token(token: str, expected_type: Optional[str] = "access") -> Optional[dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if expected_type is not None:
            token_type = payload.get("type")
            if token_type != expected_type:
                return None
        return payload
    except Exception:
        return None


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    return decode_token(token, expected_type="access")
