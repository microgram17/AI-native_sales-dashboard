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
    month TEXT NOT NULL,
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

CREATE INDEX idx_products_supplier_code ON products(supplier_code);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_orders_store_id ON orders(store_id);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_sku ON order_items(sku);
CREATE INDEX idx_market_benchmarks_supplier_period
    ON market_benchmarks(supplier_code, period_type, period_start);