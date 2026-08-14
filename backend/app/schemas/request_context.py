from __future__ import annotations

from pydantic import BaseModel


class RequestContext(BaseModel):
    """Server-verified request context.

    supplier_id is always derived from verified membership data and is never
    accepted directly from request bodies, query parameters, or an LLM.
    """

    user_id: str
    supplier_id: str
    roles: list[str]
