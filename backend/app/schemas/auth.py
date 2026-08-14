from __future__ import annotations

from pydantic import BaseModel


class VerifiedIdentity(BaseModel):
    """Identity extracted from a verified JWT."""

    subject: str
    email: str | None = None


class AppUser(BaseModel):
    """An application user loaded from the database."""

    user_id: str
    auth_subject: str
    email: str
    display_name: str | None = None
    active: bool


class SupplierMembership(BaseModel):
    """A user's membership in a supplier tenant."""

    user_id: str
    supplier_id: str
    role: str
    active: bool


class AuthMeResponse(BaseModel):
    """Response body for GET /auth/me."""

    user_id: str
    supplier_id: str
    roles: list[str]
