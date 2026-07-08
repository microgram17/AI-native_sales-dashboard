from __future__ import annotations

from pydantic import BaseModel


class UserContext(BaseModel):
    user_id: str
    display_name: str
    supplier_id: str
