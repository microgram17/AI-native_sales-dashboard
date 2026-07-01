from fastapi import Header, HTTPException

from app.tenancy.demo_users import DEMO_USERS
from app.schemas.auth import CurrentUserContext


def get_current_user_context(
    x_demo_user_id: str | None = Header(default=None),
) -> CurrentUserContext:
    if not x_demo_user_id:
        raise HTTPException(
            status_code=401,
            detail="X-Demo-User-Id header is required",
        )

    user = DEMO_USERS.get(x_demo_user_id)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail=f"Unknown demo user: {x_demo_user_id!r}",
        )

    return CurrentUserContext(
        user_id=x_demo_user_id,
        display_name=user["display_name"],
        email=user["email"],
        allowed_supplier_codes=user["supplier_codes"],
    )
