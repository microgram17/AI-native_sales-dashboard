from __future__ import annotations

from app.integrations.auth.jwt_verifier import InvalidTokenError, JwtVerifier
from app.repositories.auth_repository import AuthRepository
from app.schemas.request_context import RequestContext

# Re-exported so the API layer can catch it as a service-level exception too.
__all__ = [
    "InvalidTokenError",
    "AccessDeniedError",
    "SupplierSelectionRequiredError",
    "AuthenticationService",
]


class AccessDeniedError(Exception):
    """Raised when a verified user may not access the requested supplier context."""


class SupplierSelectionRequiredError(Exception):
    """Raised when a user has multiple memberships but selected no supplier."""


class AuthenticationService:
    """Turns a Bearer token into a trusted RequestContext.

    Owns all authentication and authorization decisions; the supplier_id is
    always resolved from server-verified membership data.
    """

    def __init__(self, verifier: JwtVerifier, repository: AuthRepository) -> None:
        self._verifier = verifier
        self._repository = repository

    def authenticate(
        self, token: str, requested_supplier_id: str | None = None
    ) -> RequestContext:
        identity = self._verifier.verify(token)

        user = self._repository.get_user_by_auth_subject(identity.subject)
        if user is None or not user.active:
            raise AccessDeniedError("Unknown or inactive application user")

        memberships = self._repository.list_active_memberships(user.user_id)
        if not memberships:
            raise AccessDeniedError("User has no active supplier memberships")

        if len(memberships) == 1 and requested_supplier_id is None:
            membership = memberships[0]
        else:
            if requested_supplier_id is None:
                raise SupplierSelectionRequiredError(
                    "Multiple supplier memberships; X-Supplier-Id header required"
                )
            membership = self._repository.get_active_membership(
                user.user_id, requested_supplier_id
            )
            if membership is None:
                raise AccessDeniedError(
                    "Requested supplier is not an active membership for this user"
                )

        return RequestContext(
            user_id=user.user_id,
            supplier_id=membership.supplier_id,
            roles=[membership.role],
        )
