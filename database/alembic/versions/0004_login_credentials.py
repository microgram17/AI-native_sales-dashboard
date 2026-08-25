from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0004_login_credentials"
down_revision: str | None = "0003_analytics_layer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "app_users",
        sa.Column(
            "password_hash",
            sa.Text(),
            nullable=True,
        ),
    )
    op.add_column(
        "app_users",
        sa.Column(
            "account_type",
            sa.Text(),
            server_default="supplier",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_app_users_account_type_valid",
        "app_users",
        "account_type IN ('supplier', 'retailer_admin')",
    )
    op.create_unique_constraint(
        "uq_app_users_email",
        "app_users",
        ["email"],
    )

    # A supplier membership must never confer retailer-wide admin access.
    # Preserve legacy rows by downgrading the old supplier-level "admin"
    # membership to the least-privileged supplier role before tightening the
    # constraint.
    op.drop_constraint(
        "ck_supplier_memberships_role_valid",
        "supplier_memberships",
        type_="check",
    )
    op.execute(
        """
        UPDATE supplier_memberships
        SET role = 'viewer'
        WHERE role = 'admin'
        """
    )
    op.create_check_constraint(
        "ck_supplier_memberships_role_valid",
        "supplier_memberships",
        "role IN ('analyst', 'viewer')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_supplier_memberships_role_valid",
        "supplier_memberships",
        type_="check",
    )
    op.create_check_constraint(
        "ck_supplier_memberships_role_valid",
        "supplier_memberships",
        "role IN ('admin', 'analyst', 'viewer')",
    )

    op.drop_constraint(
        "uq_app_users_email",
        "app_users",
        type_="unique",
    )
    op.drop_constraint(
        "ck_app_users_account_type_valid",
        "app_users",
        type_="check",
    )
    op.drop_column("app_users", "account_type")
    op.drop_column("app_users", "password_hash")
