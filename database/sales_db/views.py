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
