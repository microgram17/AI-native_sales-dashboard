DROP VIEW IF EXISTS scoped_supplier_order_line_facts;
DROP VIEW IF EXISTS supplier_order_line_facts;

DROP TABLE IF EXISTS market_benchmarks;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS stores;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS suppliers;

CREATE TABLE suppliers (
    supplier_code TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    contact_email TEXT,
    primary_brand TEXT,
    primary_category TEXT
);

CREATE TABLE products (
    sku TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    brand TEXT NOT NULL,
    category TEXT NOT NULL,
    supplier_code TEXT NOT NULL REFERENCES suppliers(supplier_code),
    unit_cost NUMERIC(12, 2) NOT NULL,
    recommended_price NUMERIC(12, 2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'SEK'
);

CREATE TABLE stores (
    store_id TEXT PRIMARY KEY,
    store_name TEXT NOT NULL,
    sales_channel TEXT NOT NULL,
    country TEXT NOT NULL,
    region TEXT NOT NULL,
    city TEXT NOT NULL
);

CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    order_date DATE NOT NULL,
    week_start DATE NOT NULL,
    month_start DATE NOT NULL,
    store_id TEXT NOT NULL REFERENCES stores(store_id),
    customer_segment TEXT NOT NULL,
    anonymized_customer_id TEXT NOT NULL
);

CREATE TABLE order_items (
    order_line_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    sku TEXT NOT NULL REFERENCES products(sku),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL,
    discount_percent NUMERIC(5, 2) NOT NULL DEFAULT 0,
    gross_sales NUMERIC(12, 2) NOT NULL,
    net_sales NUMERIC(12, 2) NOT NULL,
    estimated_margin NUMERIC(12, 2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'SEK'
);

CREATE TABLE market_benchmarks (
    id BIGSERIAL PRIMARY KEY,
    supplier_code TEXT NOT NULL REFERENCES suppliers(supplier_code),
    period_type TEXT NOT NULL CHECK (period_type IN ('week', 'month')),
    period_start DATE NOT NULL,
    period_label TEXT NOT NULL,

    supplier_revenue NUMERIC(14, 2) NOT NULL,
    supplier_units INTEGER NOT NULL,
    supplier_orders INTEGER NOT NULL,

    comparable_market_revenue NUMERIC(14, 2) NOT NULL,
    comparable_market_units INTEGER NOT NULL,
    comparable_market_orders INTEGER NOT NULL,
    estimated_market_share_pct NUMERIC(6, 2) NOT NULL,

    UNIQUE (supplier_code, period_type, period_start)
);

CREATE INDEX idx_products_supplier_code
    ON products(supplier_code);

CREATE INDEX idx_orders_order_date
    ON orders(order_date);

CREATE INDEX idx_orders_store_id
    ON orders(store_id);

CREATE INDEX idx_order_items_order_id
    ON order_items(order_id);

CREATE INDEX idx_order_items_sku
    ON order_items(sku);

CREATE INDEX idx_market_benchmarks_supplier_period
    ON market_benchmarks(supplier_code, period_type, period_start);

CREATE INDEX idx_orders_week_start
    ON orders(week_start);

CREATE INDEX idx_orders_month
    ON orders(month_start);

CREATE INDEX idx_stores_channel_region
    ON stores(sales_channel, region);

CREATE INDEX idx_products_supplier_category_brand
    ON products(supplier_code, category, brand);

CREATE OR REPLACE VIEW supplier_order_line_facts AS
SELECT
    p.supplier_code,
    s.supplier_name,

    oi.order_line_id,
    oi.order_id,
    o.order_date,
    o.week_start,
    o.month_start,
    to_char(o.month_start, 'YYYY-MM') AS month_label,

    p.sku,
    p.product_name,
    p.brand,
    p.category,
    p.unit_cost,
    p.recommended_price,

    st.store_id,
    st.store_name,
    st.sales_channel,
    st.country,
    st.region,
    st.city,

    o.customer_segment,
    o.anonymized_customer_id,

    oi.quantity,
    oi.unit_price,
    oi.discount_percent,
    oi.gross_sales,
    oi.net_sales,
    oi.estimated_margin,
    oi.currency,

    CASE
        WHEN oi.net_sales = 0 THEN NULL
        ELSE oi.estimated_margin / oi.net_sales
    END AS margin_rate,

    CASE
        WHEN p.recommended_price = 0 THEN NULL
        ELSE (oi.unit_price - p.recommended_price) / p.recommended_price
    END AS price_vs_recommended_pct

FROM order_items oi
JOIN orders o
    ON o.order_id = oi.order_id
JOIN products p
    ON p.sku = oi.sku
JOIN suppliers s
    ON s.supplier_code = p.supplier_code
JOIN stores st
    ON st.store_id = o.store_id;
