from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0002_auth_tables"
down_revision: str | None = "0001_initial_sales_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_users",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("auth_subject", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_app_users"),
        sa.UniqueConstraint("auth_subject", name="uq_app_users_auth_subject"),
    )

    op.create_table(
        "supplier_memberships",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("supplier_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'analyst', 'viewer')",
            name="ck_supplier_memberships_role_valid",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app_users.user_id"],
            name="fk_supplier_memberships_user_id_app_users",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.supplier_id"],
            name="fk_supplier_memberships_supplier_id_suppliers",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("user_id", "supplier_id", name="pk_supplier_memberships"),
    )

    op.create_index("idx_app_users_auth_subject", "app_users", ["auth_subject"])
    op.create_index("idx_supplier_memberships_user_id", "supplier_memberships", ["user_id"])
    op.create_index(
        "idx_supplier_memberships_supplier_id", "supplier_memberships", ["supplier_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_supplier_memberships_supplier_id", table_name="supplier_memberships")
    op.drop_index("idx_supplier_memberships_user_id", table_name="supplier_memberships")
    op.drop_index("idx_app_users_auth_subject", table_name="app_users")

    op.drop_table("supplier_memberships")
    op.drop_table("app_users")
