"""Idempotently seed the development auth user and supplier membership.

Rerunning is safe thanks to PostgreSQL ON CONFLICT clauses.

Usage:
    uv run python -m scripts.seed_dev_auth
"""

from __future__ import annotations

from psycopg import Connection

from sales_db.connection import get_connection


DEV_USER = {
    "user_id": "DEV-USER-001",
    "auth_subject": "dev-user",
    "email": "dev@example.com",
    "display_name": "Development User",
    "active": True,
}

DEV_MEMBERSHIP = {
    "user_id": "DEV-USER-001",
    "supplier_id": "NORDVALE",
    "role": "admin",
    "active": True,
}


def seed_user(conn: Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO app_users (
                user_id, auth_subject, email, display_name, active,
                created_at, updated_at
            )
            VALUES (
                %(user_id)s, %(auth_subject)s, %(email)s, %(display_name)s, %(active)s,
                now(), now()
            )
            ON CONFLICT (user_id) DO UPDATE SET
                auth_subject = EXCLUDED.auth_subject,
                email = EXCLUDED.email,
                display_name = EXCLUDED.display_name,
                active = EXCLUDED.active,
                updated_at = now();
            """,
            DEV_USER,
        )


def seed_membership(conn: Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO supplier_memberships (
                user_id, supplier_id, role, active, created_at
            )
            VALUES (
                %(user_id)s, %(supplier_id)s, %(role)s, %(active)s, now()
            )
            ON CONFLICT (user_id, supplier_id) DO UPDATE SET
                role = EXCLUDED.role,
                active = EXCLUDED.active;
            """,
            DEV_MEMBERSHIP,
        )


def main() -> None:
    with get_connection() as conn:
        seed_user(conn)
        seed_membership(conn)
    print(
        f"Seeded dev user {DEV_USER['user_id']} "
        f"(auth_subject={DEV_USER['auth_subject']}) with "
        f"{DEV_MEMBERSHIP['role']} membership on {DEV_MEMBERSHIP['supplier_id']}."
    )


if __name__ == "__main__":
    main()
