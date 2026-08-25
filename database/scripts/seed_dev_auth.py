"""Idempotently seed local development login accounts.

Creates one supplier account per active supplier and one retailer
admin account. Supplier accounts receive only supplier-scoped roles; retailer
admin is an application-level account type and has no supplier membership.

Usage:
    uv run python -m scripts.seed_dev_auth

Optional:
    DEMO_AUTH_PASSWORD=YourPasswordHere
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from psycopg import Connection
from pwdlib import PasswordHash

from sales_db.connection import get_connection


DEFAULT_DEMO_PASSWORD = "DemoPassword123!"
PASSWORD_HASH = PasswordHash.recommended()


@dataclass(frozen=True)
class SupplierSeed:
    supplier_id: str
    supplier_name: str


def _demo_password() -> str:
    return (
        os.getenv("DEMO_AUTH_PASSWORD")
        or DEFAULT_DEMO_PASSWORD
    )


def load_demo_suppliers(
    conn: Connection,
) -> list[SupplierSeed]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT supplier_id, supplier_name
            FROM suppliers
            WHERE active = true
            ORDER BY supplier_id
            """,
        )
        return [
            SupplierSeed(
                supplier_id=row[0],
                supplier_name=row[1],
            )
            for row in cur.fetchall()
        ]


def upsert_user(
    conn: Connection,
    *,
    user_id: str,
    auth_subject: str,
    email: str,
    display_name: str,
    password_hash: str,
    account_type: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO app_users (
                user_id,
                auth_subject,
                email,
                display_name,
                password_hash,
                account_type,
                active,
                created_at,
                updated_at
            )
            VALUES (
                %(user_id)s,
                %(auth_subject)s,
                %(email)s,
                %(display_name)s,
                %(password_hash)s,
                %(account_type)s,
                true,
                now(),
                now()
            )
            ON CONFLICT (user_id) DO UPDATE SET
                auth_subject = EXCLUDED.auth_subject,
                email = EXCLUDED.email,
                display_name = EXCLUDED.display_name,
                password_hash = EXCLUDED.password_hash,
                account_type = EXCLUDED.account_type,
                active = true,
                updated_at = now()
            """,
            {
                "user_id": user_id,
                "auth_subject": auth_subject,
                "email": email,
                "display_name": display_name,
                "password_hash": password_hash,
                "account_type": account_type,
            },
        )


def upsert_supplier_membership(
    conn: Connection,
    *,
    user_id: str,
    supplier_id: str,
    role: str = "viewer",
) -> None:
    if role == "admin":
        raise ValueError(
            "Supplier memberships cannot use the admin role"
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO supplier_memberships (
                user_id,
                supplier_id,
                role,
                active,
                created_at
            )
            VALUES (
                %(user_id)s,
                %(supplier_id)s,
                %(role)s,
                true,
                now()
            )
            ON CONFLICT (user_id, supplier_id) DO UPDATE SET
                role = EXCLUDED.role,
                active = true
            """,
            {
                "user_id": user_id,
                "supplier_id": supplier_id,
                "role": role,
            },
        )


def seed_supplier_accounts(
    conn: Connection,
    *,
    suppliers: list[SupplierSeed],
    password: str,
) -> list[tuple[str, str, str]]:
    credentials: list[tuple[str, str, str]] = []

    for index, supplier in enumerate(
        suppliers,
        start=1,
    ):
        user_id = f"DEMO-SUPPLIER-{index:03d}"
        email = f"supplier{index}@example.com"

        upsert_user(
            conn,
            user_id=user_id,
            auth_subject=f"local:{user_id}",
            email=email,
            display_name=f"{supplier.supplier_name} Demo User",
            password_hash=PASSWORD_HASH.hash(password),
            account_type="supplier",
        )
        upsert_supplier_membership(
            conn,
            user_id=user_id,
            supplier_id=supplier.supplier_id,
            role="viewer",
        )

        credentials.append(
            (email, password, supplier.supplier_id)
        )

    return credentials


def seed_retailer_admin(
    conn: Connection,
    *,
    password: str,
) -> tuple[str, str]:
    user_id = "DEMO-RETAILER-ADMIN-001"
    email = "admin@example.com"

    upsert_user(
        conn,
        user_id=user_id,
        auth_subject=f"local:{user_id}",
        email=email,
        display_name="Retailer Admin",
        password_hash=PASSWORD_HASH.hash(password),
        account_type="retailer_admin",
    )

    # Intentionally no supplier_memberships row. Retailer admin access is
    # global and supplier context is selected separately.
    return email, password


def main() -> None:
    password = _demo_password()

    with get_connection() as conn:
        suppliers = load_demo_suppliers(conn)
        if not suppliers:
            raise RuntimeError(
                "No active suppliers found. Import demo sales data first."
            )

        supplier_credentials = seed_supplier_accounts(
            conn,
            suppliers=suppliers,
            password=password,
        )
        admin_credentials = seed_retailer_admin(
            conn,
            password=password,
        )

    print("Seeded development auth accounts:")
    for email, seeded_password, supplier_id in supplier_credentials:
        print(
            f"  {email} / {seeded_password} "
            f"(supplier={supplier_id}, role=viewer)"
        )

    print(
        f"  {admin_credentials[0]} / {admin_credentials[1]} "
        "(retailer_admin; supplier-selection UI not implemented yet)"
    )


if __name__ == "__main__":
    main()
