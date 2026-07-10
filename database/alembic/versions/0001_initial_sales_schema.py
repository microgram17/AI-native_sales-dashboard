from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from sales_db.views import DROP_SUPPLIER_SALES_FACTS_VIEW, SUPPLIER_SALES_FACTS_VIEW


revision: str = "0001_initial_sales_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("supplier_id", sa.Text(), nullable=False),
        sa.Column("supplier_name", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("supplier_id", name="pk_suppliers"),
    )

    op.create_table(
        "stores",
        sa.Column("store_id", sa.Text(), nullable=False),
        sa.Column("store_name", sa.Text(), nullable=False),
        sa.Column("store_type", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("opened_date", sa.Date(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.CheckConstraint("store_type IN ('online', 'physical')", name="ck_stores_store_type_valid"),
        sa.CheckConstraint(
            """
            (
                store_type = 'online'
                AND city = 'Online'
            )
            OR (
                store_type = 'physical'
                AND city IN ('Stockholm', 'Uppsala', 'Göteborg')
            )
            """,
            name="ck_stores_online_store_city",
        ),
        sa.PrimaryKeyConstraint("store_id", name="pk_stores"),
    )

    op.create_table(
        "products",
        sa.Column("product_id", sa.Text(), nullable=False),
        sa.Column("supplier_id", sa.Text(), nullable=False),
        sa.Column("product_name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("subcategory", sa.Text(), nullable=True),
        sa.Column("base_price_sek", sa.Numeric(12, 2), nullable=False),
        sa.Column("base_cost_sek", sa.Numeric(12, 2), nullable=False),
        sa.Column("launch_date", sa.Date(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.CheckConstraint("base_price_sek >= 0", name="ck_products_base_price_nonnegative"),
        sa.CheckConstraint("base_cost_sek >= 0", name="ck_products_base_cost_nonnegative"),
        sa.CheckConstraint("base_cost_sek <= base_price_sek", name="ck_products_product_cost_below_price"),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.supplier_id"],
            name="fk_products_supplier_id_suppliers",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("product_id", name="pk_products"),
    )

    op.create_table(
        "orders",
        sa.Column("order_id", sa.Text(), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("store_id", sa.Text(), nullable=False),
        sa.Column("order_status", sa.Text(), nullable=False),
        sa.Column("payment_method", sa.Text(), nullable=False),
        sa.CheckConstraint("order_status IN ('completed', 'cancelled')", name="ck_orders_order_status_valid"),
        sa.CheckConstraint(
            "payment_method IN ('card', 'swish', 'klarna', 'gift_card')",
            name="ck_orders_payment_method_valid",
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.store_id"],
            name="fk_orders_store_id_stores",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("order_id", name="pk_orders"),
    )

    op.create_table(
        "order_items",
        sa.Column("order_item_id", sa.Text(), nullable=False),
        sa.Column("order_id", sa.Text(), nullable=False),
        sa.Column("product_id", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_sek", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_cost_sek", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_amount_sek", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.CheckConstraint("unit_price_sek >= 0", name="ck_order_items_unit_price_nonnegative"),
        sa.CheckConstraint("unit_cost_sek >= 0", name="ck_order_items_unit_cost_nonnegative"),
        sa.CheckConstraint("discount_amount_sek >= 0", name="ck_order_items_discount_nonnegative"),
        sa.CheckConstraint("unit_cost_sek <= unit_price_sek", name="ck_order_items_order_item_cost_below_price"),
        sa.CheckConstraint(
            "discount_amount_sek <= quantity * unit_price_sek",
            name="ck_order_items_order_item_discount_not_above_gross",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.order_id"],
            name="fk_order_items_order_id_orders",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.product_id"],
            name="fk_order_items_product_id_products",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("order_item_id", name="pk_order_items"),
    )

    op.create_index("idx_orders_order_date", "orders", ["order_date"])
    op.create_index("idx_orders_store_id", "orders", ["store_id"])
    op.create_index("idx_products_supplier_id", "products", ["supplier_id"])
    op.create_index("idx_products_category", "products", ["category"])
    op.create_index("idx_order_items_order_id", "order_items", ["order_id"])
    op.create_index("idx_order_items_product_id", "order_items", ["product_id"])

    op.execute(SUPPLIER_SALES_FACTS_VIEW)


def downgrade() -> None:
    op.execute(DROP_SUPPLIER_SALES_FACTS_VIEW)

    op.drop_index("idx_order_items_product_id", table_name="order_items")
    op.drop_index("idx_order_items_order_id", table_name="order_items")
    op.drop_index("idx_products_category", table_name="products")
    op.drop_index("idx_products_supplier_id", table_name="products")
    op.drop_index("idx_orders_store_id", table_name="orders")
    op.drop_index("idx_orders_order_date", table_name="orders")

    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("products")
    op.drop_table("stores")
    op.drop_table("suppliers")
