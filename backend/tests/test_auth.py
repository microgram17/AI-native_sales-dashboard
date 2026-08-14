from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_authentication_service
from app.integrations.auth.jwt_verifier import JwtVerifier
from app.main import app
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth import AppUser, SupplierMembership
from app.services.authentication_service import AuthenticationService

TEST_SECRET = "test-secret-that-is-at-least-32-bytes-long"


class FakeAuthRepository:
    """In-memory stand-in for AuthRepository (no database required)."""

    def __init__(
        self,
        user: AppUser | None = None,
        memberships: list[SupplierMembership] | None = None,
    ) -> None:
        self._user = user
        self._memberships = memberships or []

    def get_user_by_auth_subject(self, auth_subject: str) -> AppUser | None:
        if self._user is not None and self._user.auth_subject == auth_subject:
            return self._user
        return None

    def list_active_memberships(self, user_id: str) -> list[SupplierMembership]:
        return [m for m in self._memberships if m.active]

    def get_active_membership(
        self, user_id: str, supplier_id: str
    ) -> SupplierMembership | None:
        for m in self._memberships:
            if m.supplier_id == supplier_id and m.active:
                return m
        return None


def make_token(secret: str = TEST_SECRET, subject: str = "dev-user") -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": subject,
        "email": "dev@example.com",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def client_with_repo(repo: FakeAuthRepository | AuthRepository) -> TestClient:
    verifier = JwtVerifier(secret=TEST_SECRET, algorithm="HS256")
    service = AuthenticationService(verifier, repo)  # type: ignore[arg-type]
    app.dependency_overrides[get_authentication_service] = lambda: service
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def _user(active: bool = True) -> AppUser:
    return AppUser(
        user_id="DEV-USER-001",
        auth_subject="dev-user",
        email="dev@example.com",
        display_name="Development User",
        active=active,
    )


def _membership(supplier_id: str, role: str = "admin", active: bool = True) -> SupplierMembership:
    return SupplierMembership(
        user_id="DEV-USER-001",
        supplier_id=supplier_id,
        role=role,
        active=active,
    )


def test_health_no_auth() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_missing_authorization_returns_401() -> None:
    client = client_with_repo(FakeAuthRepository())
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_token_returns_401() -> None:
    client = client_with_repo(FakeAuthRepository(user=_user()))
    bad_token = make_token(secret="a-different-secret-that-is-also-32-bytes-x")
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_unknown_user_returns_403() -> None:
    client = client_with_repo(FakeAuthRepository(user=None))
    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {make_token()}"}
    )
    assert response.status_code == 403


def test_inactive_user_returns_403() -> None:
    repo = FakeAuthRepository(user=_user(active=False), memberships=[_membership("NORDVALE")])
    client = client_with_repo(repo)
    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {make_token()}"}
    )
    assert response.status_code == 403


def test_no_memberships_returns_403() -> None:
    repo = FakeAuthRepository(user=_user(), memberships=[])
    client = client_with_repo(repo)
    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {make_token()}"}
    )
    assert response.status_code == 403


def test_single_membership_selected_automatically() -> None:
    repo = FakeAuthRepository(user=_user(), memberships=[_membership("NORDVALE")])
    client = client_with_repo(repo)
    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {make_token()}"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "user_id": "DEV-USER-001",
        "supplier_id": "NORDVALE",
        "roles": ["admin"],
    }


def test_multiple_memberships_without_supplier_returns_400() -> None:
    repo = FakeAuthRepository(
        user=_user(),
        memberships=[_membership("NORDVALE"), _membership("KIDS_CO", role="viewer")],
    )
    client = client_with_repo(repo)
    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {make_token()}"}
    )
    assert response.status_code == 400


def test_cannot_select_supplier_without_membership() -> None:
    repo = FakeAuthRepository(user=_user(), memberships=[_membership("NORDVALE")])
    client = client_with_repo(repo)
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {make_token()}",
            "X-Supplier-Id": "KIDS_CO",
        },
    )
    assert response.status_code == 403


def test_valid_user_and_membership_returns_me() -> None:
    repo = FakeAuthRepository(
        user=_user(),
        memberships=[_membership("NORDVALE"), _membership("KIDS_CO", role="viewer")],
    )
    client = client_with_repo(repo)
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {make_token()}",
            "X-Supplier-Id": "KIDS_CO",
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "user_id": "DEV-USER-001",
        "supplier_id": "KIDS_CO",
        "roles": ["viewer"],
    }
