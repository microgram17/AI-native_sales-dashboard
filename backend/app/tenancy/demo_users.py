from __future__ import annotations

DEMO_USERS: dict[str, dict] = {
    "demo-user-nordic": {
        "display_name": "Nordic Demo User",
        "email": "nordic@demo.dev",
        "supplier_codes": ["SUP-001"],
    },
    "demo-user-smart": {
        "display_name": "Smart Living Demo",
        "email": "smart@demo.dev",
        "supplier_codes": ["SUP-005"],
    },
    "demo-user-admin": {
        "display_name": "Admin",
        "email": "admin@demo.dev",
        "supplier_codes": ["SUP-001", "SUP-002", "SUP-003", "SUP-004", "SUP-005"],
    },
}


def get_allowed_suppliers(user_id: str) -> list[str] | None:
    user = DEMO_USERS.get(user_id)
    return user["supplier_codes"] if user else None


def list_demo_users() -> list[dict]:
    return [
        {
            "user_id": uid,
            "display_name": data["display_name"],
            "email": data["email"],
            "supplier_codes": data["supplier_codes"],
        }
        for uid, data in DEMO_USERS.items()
    ]
