from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Table,
    Text,
    TIMESTAMP,
    text,
)

from sales_db.metadata import metadata


suppliers = Table(
    "suppliers",
    metadata,
    Column("supplier_id", Text, primary_key=True),
    Column("supplier_name", Text, nullable=False),
    Column("active", Boolean, nullable=False, server_default="true"),
)

stores = Table(
    "stores",
    metadata,
    Column("store_id", Text, primary_key=True),
    Column("store_name", Text, nullable=False),
    Column("store_type", Text, nullable=False),
    Column("city", Text, nullable=False),
    Column("opened_date", Date, nullable=False),
    Column("active", Boolean, nullable=False, server_default="true"),
    CheckConstraint("store_type IN ('online', 'physical')", name="store_type_valid"),
    CheckConstraint(
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
        name="online_store_city",
    ),
)

products = Table(
    "products",
    metadata,
    Column("product_id", Text, primary_key=True),
    Column(
        "supplier_id",
        Text,
        ForeignKey("suppliers.supplier_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("product_name", Text, nullable=False),
    Column("category", Text, nullable=False),
    Column("subcategory", Text),
    Column("base_price_sek", Numeric(12, 2), nullable=False),
    Column("base_cost_sek", Numeric(12, 2), nullable=False),
    Column("launch_date", Date, nullable=False),
    Column("active", Boolean, nullable=False, server_default="true"),
    CheckConstraint("base_price_sek >= 0", name="base_price_nonnegative"),
    CheckConstraint("base_cost_sek >= 0", name="base_cost_nonnegative"),
    CheckConstraint("base_cost_sek <= base_price_sek", name="product_cost_below_price"),
)

orders = Table(
    "orders",
    metadata,
    Column("order_id", Text, primary_key=True),
    Column("order_date", Date, nullable=False),
    Column(
        "store_id",
        Text,
        ForeignKey("stores.store_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("order_status", Text, nullable=False),
    Column("payment_method", Text, nullable=False),
    CheckConstraint("order_status IN ('completed', 'cancelled')", name="order_status_valid"),
    CheckConstraint(
        "payment_method IN ('card', 'swish', 'klarna', 'gift_card')",
        name="payment_method_valid",
    ),
)

order_items = Table(
    "order_items",
    metadata,
    Column("order_item_id", Text, primary_key=True),
    Column(
        "order_id",
        Text,
        ForeignKey("orders.order_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "product_id",
        Text,
        ForeignKey("products.product_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("quantity", Integer, nullable=False),
    Column("unit_price_sek", Numeric(12, 2), nullable=False),
    Column("unit_cost_sek", Numeric(12, 2), nullable=False),
    Column("discount_amount_sek", Numeric(12, 2), nullable=False, server_default="0"),
    CheckConstraint("quantity > 0", name="quantity_positive"),
    CheckConstraint("unit_price_sek >= 0", name="unit_price_nonnegative"),
    CheckConstraint("unit_cost_sek >= 0", name="unit_cost_nonnegative"),
    CheckConstraint("discount_amount_sek >= 0", name="discount_nonnegative"),
    CheckConstraint("unit_cost_sek <= unit_price_sek", name="order_item_cost_below_price"),
    CheckConstraint(
        "discount_amount_sek <= quantity * unit_price_sek",
        name="order_item_discount_not_above_gross",
    ),
)

app_users = Table(
    "app_users",
    metadata,
    Column("user_id", Text, primary_key=True),
    Column("auth_subject", Text, nullable=False, unique=True),
    Column("email", Text, nullable=False, unique=True),
    Column("display_name", Text),
    Column("password_hash", Text),
    Column("account_type", Text, nullable=False, server_default="supplier"),
    Column("active", Boolean, nullable=False, server_default="true"),
    CheckConstraint(
        "account_type IN ('supplier', 'retailer_admin')",
        name="app_user_account_type_valid",
    ),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
)

supplier_memberships = Table(
    "supplier_memberships",
    metadata,
    Column(
        "user_id",
        Text,
        ForeignKey("app_users.user_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "supplier_id",
        Text,
        ForeignKey("suppliers.supplier_id", onupdate="CASCADE", ondelete="RESTRICT"),
        primary_key=True,
    ),
    Column("role", Text, nullable=False),
    Column("active", Boolean, nullable=False, server_default="true"),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    CheckConstraint("role IN ('analyst', 'viewer')", name="role_valid"),
)

Index("idx_orders_order_date", orders.c.order_date)
Index("idx_orders_store_id", orders.c.store_id)
Index("idx_products_supplier_id", products.c.supplier_id)
Index("idx_products_category", products.c.category)
Index("idx_order_items_order_id", order_items.c.order_id)
Index("idx_order_items_product_id", order_items.c.product_id)
Index("idx_app_users_auth_subject", app_users.c.auth_subject)
Index("idx_supplier_memberships_user_id", supplier_memberships.c.user_id)
Index("idx_supplier_memberships_supplier_id", supplier_memberships.c.supplier_id)


dim_date = Table(
    "dim_date",
    metadata,
    Column("date_key", Date, primary_key=True),
    Column("calendar_year", Integer, nullable=False),
    Column("calendar_quarter", Integer, nullable=False),
    Column("calendar_month", Integer, nullable=False),
    Column("month_name", Text, nullable=False),
    Column("month_start", Date, nullable=False),
    Column("month_end", Date, nullable=False),
    Column("quarter_start", Date, nullable=False),
    Column("quarter_end", Date, nullable=False),
    Column("iso_year", Integer, nullable=False),
    Column("iso_week", Integer, nullable=False),
    Column("week_start", Date, nullable=False),
    Column("week_end", Date, nullable=False),
    Column("is_weekend", Boolean, nullable=False),
)
