from dataclasses import dataclass

from fastapi import Header, HTTPException

from app.tenancy.demo_users import get_allowed_suppliers, DEMO_USERS


@dataclass
class UserContext:
    user_id: str
    display_name: str
    allowed_suppliers: list[str]


def get_user_context(x_demo_user: str | None = Header(default=None)) -> UserContext:
    if not x_demo_user:
        raise HTTPException(status_code=400, detail="X-Demo-User header is required")

    user = DEMO_USERS.get(x_demo_user)
    if user is None:
        raise HTTPException(status_code=403, detail=f"Unknown demo user: {x_demo_user!r}")

    return UserContext(
        user_id=x_demo_user,
        display_name=user["display_name"],
        allowed_suppliers=user["supplier_codes"],
    )
