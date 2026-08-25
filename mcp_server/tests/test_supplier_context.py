"""Tests for JWT-based supplier context resolution (no DB, no server)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest

from app.context.supplier_context import SupplierContextError, SupplierContextResolver
from tests.conftest import JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET, SUPPLIER


def _ctx(authorization: str | None):
    headers = {"authorization": authorization} if authorization is not None else {}
    return SimpleNamespace(
        request_context=SimpleNamespace(request=SimpleNamespace(headers=headers))
    )


def _token(
    *,
    supplier_id: str = SUPPLIER,
    secret: str = JWT_SECRET,
    issuer: str = JWT_ISSUER,
    audience: str = JWT_AUDIENCE,
    ttl_seconds: int = 120,
) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": "DEV-USER-001",
        "supplier_id": supplier_id,
        "roles": ["admin"],
        "iss": issuer,
        "aud": audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _resolver():
    return SupplierContextResolver(
        jwt_secret=JWT_SECRET,
        jwt_issuer=JWT_ISSUER,
        jwt_audience=JWT_AUDIENCE,
    )


def test_valid_token_resolves_supplier():
    resolver = _resolver()
    assert resolver.resolve(_ctx(f"Bearer {_token(supplier_id='KIDS_CO')}")) == "KIDS_CO"


def test_invalid_signature_rejected():
    resolver = _resolver()
    bad = _token(secret="wrong-secret")
    with pytest.raises(SupplierContextError):
        resolver.resolve(_ctx(f"Bearer {bad}"))


def test_expired_token_rejected():
    resolver = _resolver()
    expired = _token(ttl_seconds=-10)
    with pytest.raises(SupplierContextError):
        resolver.resolve(_ctx(f"Bearer {expired}"))


def test_wrong_issuer_rejected():
    resolver = _resolver()
    with pytest.raises(SupplierContextError):
        resolver.resolve(_ctx(f"Bearer {_token(issuer='evil')}"))


def test_wrong_audience_rejected():
    resolver = _resolver()
    with pytest.raises(SupplierContextError):
        resolver.resolve(_ctx(f"Bearer {_token(audience='evil')}"))


def test_missing_authentication_fails():
    resolver = _resolver()
    with pytest.raises(SupplierContextError):
        resolver.resolve(_ctx(None))


def test_two_supplier_tokens_isolated():
    resolver = _resolver()
    a = resolver.resolve(_ctx(f"Bearer {_token(supplier_id='NORDVALE')}"))
    b = resolver.resolve(_ctx(f"Bearer {_token(supplier_id='KIDS_CO')}"))
    assert a == "NORDVALE"
    assert b == "KIDS_CO"
    assert a != b
