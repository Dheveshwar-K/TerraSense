import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token

def test_password_hashing():
    pwd = "IndustrialQuality4.0"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_token():
    payload = {"sub": "quality_engineer", "role": "quality_engineer"}
    token = create_access_token(payload)
    decoded = decode_access_token(token)
    assert decoded["sub"] == "quality_engineer"
    assert decoded["role"] == "quality_engineer"
