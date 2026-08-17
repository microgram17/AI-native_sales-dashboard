from __future__ import annotations

from pydantic import BaseModel

from app.schemas.auth import AccountType


class RequestContext(BaseModel):
    """Server-verified request context.

    supplier_id is always derived from verified membership data or, for a
    retailer admin, from a server-authorized supplier selection. It is never
    accepted from request bodies, query parameters, or an LLM.
    """

    user_id: str
    supplier_id: str
    roles: list[str]
    email: str | None = None
    display_name: str | None = None
    account_type: AccountType = "supplier"
