from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


AccountType = Literal["supplier", "retailer_admin"]


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
    password_hash: str | None = None
    account_type: AccountType = "supplier"
    active: bool


class SupplierMembership(BaseModel):
    """A user's membership in a supplier tenant."""

    user_id: str
    supplier_id: str
    role: str
    active: bool


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=512)


class AuthLoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    account_type: AccountType


class AuthMeResponse(BaseModel):
    """Response body for GET /auth/me."""

    user_id: str
    email: str | None = None
    display_name: str | None = None
    account_type: AccountType
    supplier_id: str
    roles: list[str]
