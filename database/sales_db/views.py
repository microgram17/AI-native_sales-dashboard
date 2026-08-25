from __future__ import annotations


SUPPLIER_SALES_FACTS_VIEW = """
CREATE OR REPLACE VIEW v_supplier_sales_facts AS
SELECT
    p.supplier_id,
    sup.supplier_name,
    p.product_id,
    p.product_name,
    p.category,
    p.subcategory,
    st.store_id,
    st.store_name,
    st.city,
    CASE
        WHEN st.store_type = 'online' THEN 'online'
        ELSE 'physical'
    END AS channel,
    o.order_id,
    o.order_date,
    oi.quantity,
    ROUND((oi.quantity * oi.unit_price_sek)::numeric, 2) AS gross_sales,
    ROUND((oi.quantity * oi.unit_price_sek - oi.discount_amount_sek)::numeric, 2) AS net_sales,
    oi.discount_amount_sek AS discounts
FROM order_items oi
JOIN orders o
    ON o.order_id = oi.order_id
JOIN products p
    ON p.product_id = oi.product_id
JOIN suppliers sup
    ON sup.supplier_id = p.supplier_id
JOIN stores st
    ON st.store_id = o.store_id
WHERE o.order_status = 'completed';
"""

DROP_SUPPLIER_SALES_FACTS_VIEW = "DROP VIEW IF EXISTS v_supplier_sales_facts;"


# ── Daily analytical aggregates ────────────────────────────────────────────────
# These pre-aggregate v_supplier_sales_facts to daily grain at three entity
# levels. Distinct order counts are computed directly at each view's grain and
# are NOT safely additive across the entity axis (a single order can contain
# several products/categories), which is why three separate grains exist.

PRODUCT_STORE_DAILY_SALES_VIEW = """
CREATE OR REPLACE VIEW v_product_store_daily_sales AS
SELECT
    f.supplier_id,
    f.order_date AS sales_date,
    f.product_id,
    f.product_name,
    f.category,
    f.store_id,
    f.store_name,
    f.city,
    f.channel,
    SUM(f.quantity) AS units,
    ROUND(SUM(f.gross_sales)::numeric, 2) AS gross_sales,
    ROUND(SUM(f.net_sales)::numeric, 2) AS net_sales,
    ROUND(SUM(f.discounts)::numeric, 2) AS discounts,
    COUNT(DISTINCT f.order_id) AS orders
FROM v_supplier_sales_facts f
GROUP BY
    f.supplier_id,
    f.order_date,
    f.product_id,
    f.product_name,
    f.category,
    f.store_id,
    f.store_name,
    f.city,
    f.channel;
"""

CATEGORY_STORE_DAILY_SALES_VIEW = """
CREATE OR REPLACE VIEW v_category_store_daily_sales AS
SELECT
    f.supplier_id,
    f.order_date AS sales_date,
    f.category,
    f.store_id,
    f.store_name,
    f.city,
    f.channel,
    SUM(f.quantity) AS units,
    ROUND(SUM(f.gross_sales)::numeric, 2) AS gross_sales,
    ROUND(SUM(f.net_sales)::numeric, 2) AS net_sales,
    ROUND(SUM(f.discounts)::numeric, 2) AS discounts,
    COUNT(DISTINCT f.order_id) AS orders
FROM v_supplier_sales_facts f
GROUP BY
    f.supplier_id,
    f.order_date,
    f.category,
    f.store_id,
    f.store_name,
    f.city,
    f.channel;
"""

SUPPLIER_STORE_DAILY_SALES_VIEW = """
CREATE OR REPLACE VIEW v_supplier_store_daily_sales AS
SELECT
    f.supplier_id,
    f.order_date AS sales_date,
    f.store_id,
    f.store_name,
    f.city,
    f.channel,
    SUM(f.quantity) AS units,
    ROUND(SUM(f.gross_sales)::numeric, 2) AS gross_sales,
    ROUND(SUM(f.net_sales)::numeric, 2) AS net_sales,
    ROUND(SUM(f.discounts)::numeric, 2) AS discounts,
    COUNT(DISTINCT f.order_id) AS orders
FROM v_supplier_sales_facts f
GROUP BY
    f.supplier_id,
    f.order_date,
    f.store_id,
    f.store_name,
    f.city,
    f.channel;
"""

DROP_PRODUCT_STORE_DAILY_SALES_VIEW = "DROP VIEW IF EXISTS v_product_store_daily_sales;"
DROP_CATEGORY_STORE_DAILY_SALES_VIEW = "DROP VIEW IF EXISTS v_category_store_daily_sales;"
DROP_SUPPLIER_STORE_DAILY_SALES_VIEW = "DROP VIEW IF EXISTS v_supplier_store_daily_sales;"