from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_authentication_service
from app.integrations.auth.jwt_issuer import JwtIssuer
from app.integrations.auth.jwt_verifier import JwtVerifier
from app.integrations.auth.password_hasher import PasswordHasher
from app.main import app
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth import AppUser, SupplierMembership
from app.services.authentication_service import AuthenticationService


TEST_SECRET = "test-secret-that-is-at-least-32-bytes-long"
TEST_PASSWORD = "CorrectHorseBatteryStaple!"


class FakeAuthRepository:
    """In-memory stand-in for AuthRepository (no database required)."""

    def __init__(
        self,
        user: AppUser | None = None,
        memberships: list[SupplierMembership] | None = None,
        supplier_ids: set[str] | None = None,
    ) -> None:
        self._user = user
        self._memberships = memberships or []
        self._supplier_ids = supplier_ids or {
            membership.supplier_id
            for membership in self._memberships
        }

    def get_user_by_auth_subject(
        self,
        auth_subject: str,
    ) -> AppUser | None:
        if (
            self._user is not None
            and self._user.auth_subject == auth_subject
        ):
            return self._user
        return None

    def get_user_by_email(
        self,
        email: str,
    ) -> AppUser | None:
        if (
            self._user is not None
            and self._user.email.lower() == email.strip().lower()
        ):
            return self._user
        return None

    def list_active_memberships(
        self,
        user_id: str,
    ) -> list[SupplierMembership]:
        return [
            membership
            for membership in self._memberships
            if membership.active
        ]

    def get_active_membership(
        self,
        user_id: str,
        supplier_id: str,
    ) -> SupplierMembership | None:
        for membership in self._memberships:
            if (
                membership.user_id == user_id
                and membership.supplier_id == supplier_id
                and membership.active
            ):
                return membership
        return None

    def supplier_exists(
        self,
        supplier_id: str,
    ) -> bool:
        return supplier_id in self._supplier_ids


_PASSWORD_HASHER = PasswordHasher()


def make_token(
    secret: str = TEST_SECRET,
    subject: str = "dev-user",
) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": subject,
        "email": "dev@example.com",
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(hours=1)).timestamp()
        ),
    }
    return jwt.encode(
        payload,
        secret,
        algorithm="HS256",
    )


def client_with_repo(
    repo: FakeAuthRepository | AuthRepository,
) -> TestClient:
    verifier = JwtVerifier(
        secret=TEST_SECRET,
        algorithm="HS256",
    )
    issuer = JwtIssuer(
        secret=TEST_SECRET,
        algorithm="HS256",
        ttl_seconds=3600,
    )
    service = AuthenticationService(
        verifier,
        repo,  # type: ignore[arg-type]
        issuer,
        _PASSWORD_HASHER,
    )
    app.dependency_overrides[
        get_authentication_service
    ] = lambda: service
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def _user(
    *,
    active: bool = True,
    account_type: str = "supplier",
    with_password: bool = True,
) -> AppUser:
    return AppUser(
        user_id="DEV-USER-001",
        auth_subject="dev-user",
        email="dev@example.com",
        display_name="Development User",
        password_hash=(
            _PASSWORD_HASHER.hash(TEST_PASSWORD)
            if with_password
            else None
        ),
        account_type=account_type,  # type: ignore[arg-type]
        active=active,
    )


def _membership(
    supplier_id: str,
    role: str = "viewer",
    active: bool = True,
) -> SupplierMembership:
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


def test_login_returns_access_token() -> None:
    repo = FakeAuthRepository(
        user=_user(),
        memberships=[_membership("NORDVALE")],
    )
    client = client_with_repo(repo)

    response = client.post(
        "/auth/login",
        json={
            "email": "DEV@EXAMPLE.COM",
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert body["account_type"] == "supplier"
    assert isinstance(body["access_token"], str)

    me = client.get(
        "/auth/me",
        headers={
            "Authorization": (
                f"Bearer {body['access_token']}"
            )
        },
    )
    assert me.status_code == 200
    assert me.json()["supplier_id"] == "NORDVALE"


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("unknown@example.com", TEST_PASSWORD),
        ("dev@example.com", "wrong-password"),
    ],
)
def test_login_rejects_invalid_credentials(
    email: str,
    password: str,
) -> None:
    repo = FakeAuthRepository(
        user=_user(),
        memberships=[_membership("NORDVALE")],
    )
    client = client_with_repo(repo)

    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid email or password"
    )


def test_login_rejects_inactive_user() -> None:
    repo = FakeAuthRepository(user=_user(active=False))
    client = client_with_repo(repo)

    response = client.post(
        "/auth/login",
        json={
            "email": "dev@example.com",
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 401


def test_missing_authorization_returns_401() -> None:
    client = client_with_repo(FakeAuthRepository())
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_token_returns_401() -> None:
    client = client_with_repo(
        FakeAuthRepository(user=_user())
    )
    bad_token = make_token(
        secret=(
            "a-different-secret-that-is-also-32-bytes-x"
        )
    )
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {bad_token}"
        },
    )
    assert response.status_code == 401


def test_unknown_user_returns_403() -> None:
    client = client_with_repo(
        FakeAuthRepository(user=None)
    )
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {make_token()}"
        },
    )
    assert response.status_code == 403


def test_inactive_user_returns_403() -> None:
    repo = FakeAuthRepository(
        user=_user(active=False),
        memberships=[_membership("NORDVALE")],
    )
    client = client_with_repo(repo)
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {make_token()}"
        },
    )
    assert response.status_code == 403


def test_no_memberships_returns_403() -> None:
    repo = FakeAuthRepository(
        user=_user(),
        memberships=[],
    )
    client = client_with_repo(repo)
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {make_token()}"
        },
    )
    assert response.status_code == 403


def test_single_membership_selected_automatically() -> None:
    repo = FakeAuthRepository(
        user=_user(),
        memberships=[_membership("NORDVALE")],
    )
    client = client_with_repo(repo)
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {make_token()}"
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "DEV-USER-001",
        "email": "dev@example.com",
        "display_name": "Development User",
        "account_type": "supplier",
        "supplier_id": "NORDVALE",
        "roles": ["viewer"],
    }


def test_multiple_memberships_without_supplier_returns_400() -> None:
    repo = FakeAuthRepository(
        user=_user(),
        memberships=[
            _membership("NORDVALE"),
            _membership("KIDS_CO", role="analyst"),
        ],
    )
    client = client_with_repo(repo)
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {make_token()}"
        },
    )
    assert response.status_code == 400


def test_supplier_cannot_select_supplier_without_membership() -> None:
    repo = FakeAuthRepository(
        user=_user(),
        memberships=[_membership("NORDVALE")],
    )
    client = client_with_repo(repo)
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {make_token()}",
            "X-Supplier-Id": "KIDS_CO",
        },
    )
    assert response.status_code == 403


def test_supplier_membership_cannot_grant_admin() -> None:
    repo = FakeAuthRepository(
        user=_user(),
        memberships=[
            _membership("NORDVALE", role="admin")
        ],
    )
    client = client_with_repo(repo)

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {make_token()}"
        },
    )

    assert response.status_code == 403


def test_retailer_admin_requires_supplier_selection() -> None:
    repo = FakeAuthRepository(
        user=_user(account_type="retailer_admin"),
        supplier_ids={"NORDVALE", "KIDS_CO"},
    )
    client = client_with_repo(repo)

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {make_token()}"
        },
    )

    assert response.status_code == 400


def test_retailer_admin_can_select_any_active_supplier() -> None:
    repo = FakeAuthRepository(
        user=_user(account_type="retailer_admin"),
        supplier_ids={"NORDVALE", "KIDS_CO"},
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
        "email": "dev@example.com",
        "display_name": "Development User",
        "account_type": "retailer_admin",
        "supplier_id": "KIDS_CO",
        "roles": ["retailer_admin"],
    }
