from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.engine import Connection

from app.db.tables import app_users, supplier_memberships
from app.schemas.auth import AppUser, SupplierMembership


class AuthRepository:
    """Read-only PostgreSQL access for authentication data.

    Contains only parameterized queries; it makes no authorization decisions
    and never decodes tokens or raises HTTP errors.
    """

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get_user_by_auth_subject(self, auth_subject: str) -> AppUser | None:
        stmt = select(
            app_users.c.user_id,
            app_users.c.auth_subject,
            app_users.c.email,
            app_users.c.display_name,
            app_users.c.active,
        ).where(app_users.c.auth_subject == auth_subject)

        row = self._connection.execute(stmt).mappings().first()
        if row is None:
            return None
        return AppUser(**row)

    def list_active_memberships(self, user_id: str) -> list[SupplierMembership]:
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
        self, user_id: str, supplier_id: str
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
