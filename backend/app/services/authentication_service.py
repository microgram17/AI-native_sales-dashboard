from __future__ import annotations

from app.integrations.auth.jwt_issuer import JwtIssuer
from app.integrations.auth.jwt_verifier import (
    InvalidTokenError,
    JwtVerifier,
)
from app.integrations.auth.password_hasher import PasswordHasher
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth import AuthLoginResponse
from app.schemas.request_context import RequestContext


# Re-exported so the API layer can catch service-level auth exceptions.
__all__ = [
    "InvalidTokenError",
    "InvalidCredentialsError",
    "AccessDeniedError",
    "SupplierSelectionRequiredError",
    "AuthenticationService",
]


class InvalidCredentialsError(Exception):
    """Raised when email/password authentication fails."""


class AccessDeniedError(Exception):
    """Raised when a verified user may not access the requested context."""


class SupplierSelectionRequiredError(Exception):
    """Raised when a user must select a supplier before accessing data."""


class AuthenticationService:
    """Owns login plus trusted user/supplier context resolution."""

    def __init__(
        self,
        verifier: JwtVerifier,
        repository: AuthRepository,
        issuer: JwtIssuer,
        password_hasher: PasswordHasher,
    ) -> None:
        self._verifier = verifier
        self._repository = repository
        self._issuer = issuer
        self._password_hasher = password_hasher

    def login(
        self,
        email: str,
        password: str,
    ) -> AuthLoginResponse:
        user = self._repository.get_user_by_email(email)

        if (
            user is None
            or not user.active
            or not user.password_hash
            or not self._password_hasher.verify(
                password,
                user.password_hash,
            )
        ):
            # Keep this deliberately generic so login does not reveal whether
            # an email address exists.
            raise InvalidCredentialsError(
                "Invalid email or password"
            )

        access_token = self._issuer.issue(
            subject=user.auth_subject,
            email=user.email,
        )

        return AuthLoginResponse(
            access_token=access_token,
            expires_in=self._issuer.ttl_seconds,
            account_type=user.account_type,
        )

    def authenticate(
        self,
        token: str,
        requested_supplier_id: str | None = None,
    ) -> RequestContext:
        identity = self._verifier.verify(token)

        user = self._repository.get_user_by_auth_subject(
            identity.subject
        )
        if user is None or not user.active:
            raise AccessDeniedError(
                "Unknown or inactive application user"
            )

        if user.account_type == "retailer_admin":
            return self._authenticate_retailer_admin(
                user=user,
                requested_supplier_id=requested_supplier_id,
            )

        return self._authenticate_supplier_user(
            user=user,
            requested_supplier_id=requested_supplier_id,
        )

    def _authenticate_supplier_user(
        self,
        *,
        user,
        requested_supplier_id: str | None,
    ) -> RequestContext:
        memberships = self._repository.list_active_memberships(
            user.user_id
        )
        if not memberships:
            raise AccessDeniedError(
                "User has no active supplier memberships"
            )

        if (
            len(memberships) == 1
            and requested_supplier_id is None
        ):
            membership = memberships[0]
        else:
            if requested_supplier_id is None:
                raise SupplierSelectionRequiredError(
                    "Multiple supplier memberships; "
                    "X-Supplier-Id header required"
                )

            membership = self._repository.get_active_membership(
                user.user_id,
                requested_supplier_id,
            )
            if membership is None:
                raise AccessDeniedError(
                    "Requested supplier is not an active "
                    "membership for this user"
                )

        # Supplier accounts can never gain the global retailer_admin role from
        # a supplier membership.
        if membership.role == "admin":
            raise AccessDeniedError(
                "Invalid supplier membership role"
            )

        return RequestContext(
            user_id=user.user_id,
            supplier_id=membership.supplier_id,
            roles=[membership.role],
            email=user.email,
            display_name=user.display_name,
            account_type=user.account_type,
        )

    def _authenticate_retailer_admin(
        self,
        *,
        user,
        requested_supplier_id: str | None,
    ) -> RequestContext:
        # The backend supports retailer admins selecting any active supplier.
        # The current supplier dashboard UI does not expose this selector yet.
        if requested_supplier_id is None:
            raise SupplierSelectionRequiredError(
                "Retailer admin must select a supplier with "
                "X-Supplier-Id"
            )

        if not self._repository.supplier_exists(
            requested_supplier_id
        ):
            raise AccessDeniedError(
                "Requested supplier does not exist or is inactive"
            )

        return RequestContext(
            user_id=user.user_id,
            supplier_id=requested_supplier_id,
            roles=["retailer_admin"],
            email=user.email,
            display_name=user.display_name,
            account_type=user.account_type,
        )
