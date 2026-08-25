from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.engine import Connection

from app.db.tables import app_users, supplier_memberships, suppliers
from app.schemas.auth import AppUser, SupplierMembership


class AuthRepository:
    """PostgreSQL access for authentication and authorization data.

    Contains only parameterized queries; it makes no authorization decisions
    and never decodes tokens or raises HTTP errors.
    """

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def _user_from_row(self, row) -> AppUser | None:
        if row is None:
            return None
        return AppUser(**row)

    def get_user_by_auth_subject(
        self,
        auth_subject: str,
    ) -> AppUser | None:
        stmt = select(
            app_users.c.user_id,
            app_users.c.auth_subject,
            app_users.c.email,
            app_users.c.display_name,
            app_users.c.password_hash,
            app_users.c.account_type,
            app_users.c.active,
        ).where(app_users.c.auth_subject == auth_subject)

        row = self._connection.execute(stmt).mappings().first()
        return self._user_from_row(row)

    def get_user_by_email(self, email: str) -> AppUser | None:
        normalized_email = email.strip().lower()
        stmt = select(
            app_users.c.user_id,
            app_users.c.auth_subject,
            app_users.c.email,
            app_users.c.display_name,
            app_users.c.password_hash,
            app_users.c.account_type,
            app_users.c.active,
        ).where(func.lower(app_users.c.email) == normalized_email)

        row = self._connection.execute(stmt).mappings().first()
        return self._user_from_row(row)

    def list_active_memberships(
        self,
        user_id: str,
    ) -> list[SupplierMembership]:
        stmt = (
            select(
                supplier_memberships.c.user_id,
                supplier_memberships.c.supplier_id,
                supplier_memberships.c.role,
                supplier_memberships.c.active,
            )
            .where(supplier_memberships.c.user_id == user_id)
            .where(supplier_memberships.c.active.is_(True))
        )

        rows = self._connection.execute(stmt).mappings().all()
        return [SupplierMembership(**row) for row in rows]

    def get_active_membership(
        self,
        user_id: str,
        supplier_id: str,
    ) -> SupplierMembership | None:
        stmt = (
            select(
                supplier_memberships.c.user_id,
                supplier_memberships.c.supplier_id,
                supplier_memberships.c.role,
                supplier_memberships.c.active,
            )
            .where(supplier_memberships.c.user_id == user_id)
            .where(supplier_memberships.c.supplier_id == supplier_id)
            .where(supplier_memberships.c.active.is_(True))
        )

        row = self._connection.execute(stmt).mappings().first()
        if row is None:
            return None
        return SupplierMembership(**row)

    def supplier_exists(self, supplier_id: str) -> bool:
        stmt = select(suppliers.c.supplier_id).where(
            suppliers.c.supplier_id == supplier_id,
            suppliers.c.active.is_(True),
        )
        return self._connection.execute(stmt).first() is not None
