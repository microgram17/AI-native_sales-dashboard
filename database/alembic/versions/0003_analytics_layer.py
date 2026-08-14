from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from sales_db.views import (
    CATEGORY_STORE_DAILY_SALES_VIEW,
    DROP_CATEGORY_STORE_DAILY_SALES_VIEW,
    DROP_PRODUCT_STORE_DAILY_SALES_VIEW,
    DROP_SUPPLIER_STORE_DAILY_SALES_VIEW,
    PRODUCT_STORE_DAILY_SALES_VIEW,
    SUPPLIER_STORE_DAILY_SALES_VIEW,
)


revision: str = "0003_analytics_layer"
down_revision: str | None = "0002_auth_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Populate dim_date idempotently for a wide range using generate_series.
POPULATE_DIM_DATE = """
INSERT INTO dim_date (
    date_key,
    calendar_year,
    calendar_quarter,
    calendar_month,
    month_name,
    month_start,
    month_end,
    quarter_start,
    quarter_end,
    iso_year,
    iso_week,
    week_start,
    week_end,
    is_weekend
)
SELECT
    d::date AS date_key,
    EXTRACT(YEAR FROM d)::int AS calendar_year,
    EXTRACT(QUARTER FROM d)::int AS calendar_quarter,
    EXTRACT(MONTH FROM d)::int AS calendar_month,
    TRIM(TO_CHAR(d, 'Month')) AS month_name,
    date_trunc('month', d)::date AS month_start,
    (date_trunc('month', d) + INTERVAL '1 month - 1 day')::date AS month_end,
    date_trunc('quarter', d)::date AS quarter_start,
    (date_trunc('quarter', d) + INTERVAL '3 months - 1 day')::date AS quarter_end,
    EXTRACT(ISOYEAR FROM d)::int AS iso_year,
    EXTRACT(WEEK FROM d)::int AS iso_week,
    date_trunc('week', d)::date AS week_start,
    (date_trunc('week', d) + INTERVAL '6 days')::date AS week_end,
    (EXTRACT(ISODOW FROM d) >= 6) AS is_weekend
FROM generate_series('2020-01-01'::date, '2035-12-31'::date, INTERVAL '1 day') AS d
ON CONFLICT (date_key) DO NOTHING;
"""


def upgrade() -> None:
    op.create_table(
        "dim_date",
        sa.Column("date_key", sa.Date(), nullable=False),
        sa.Column("calendar_year", sa.Integer(), nullable=False),
        sa.Column("calendar_quarter", sa.Integer(), nullable=False),
        sa.Column("calendar_month", sa.Integer(), nullable=False),
        sa.Column("month_name", sa.Text(), nullable=False),
        sa.Column("month_start", sa.Date(), nullable=False),
        sa.Column("month_end", sa.Date(), nullable=False),
        sa.Column("quarter_start", sa.Date(), nullable=False),
        sa.Column("quarter_end", sa.Date(), nullable=False),
        sa.Column("iso_year", sa.Integer(), nullable=False),
        sa.Column("iso_week", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("is_weekend", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("date_key", name="pk_dim_date"),
    )
    op.create_index("idx_dim_date_calendar_year", "dim_date", ["calendar_year"])
    op.create_index("idx_dim_date_month_start", "dim_date", ["month_start"])

    op.execute(POPULATE_DIM_DATE)

    op.execute(PRODUCT_STORE_DAILY_SALES_VIEW)
    op.execute(CATEGORY_STORE_DAILY_SALES_VIEW)
    op.execute(SUPPLIER_STORE_DAILY_SALES_VIEW)


def downgrade() -> None:
    op.execute(DROP_SUPPLIER_STORE_DAILY_SALES_VIEW)
    op.execute(DROP_CATEGORY_STORE_DAILY_SALES_VIEW)
    op.execute(DROP_PRODUCT_STORE_DAILY_SALES_VIEW)

    op.drop_index("idx_dim_date_month_start", table_name="dim_date")
    op.drop_index("idx_dim_date_calendar_year", table_name="dim_date")
    op.drop_table("dim_date")
