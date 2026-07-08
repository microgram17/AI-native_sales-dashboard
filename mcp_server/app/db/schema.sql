CREATE TABLE suppliers (
    supplier_id TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);


CREATE TABLE stores (
    store_id TEXT PRIMARY KEY,
    store_name TEXT NOT NULL,

    store_type TEXT NOT NULL CHECK (
        store_type IN ('online', 'physical')
    ),

    city TEXT NOT NULL,

    opened_date DATE NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT chk_online_store_city
        CHECK (
            (store_type = 'online' AND city = 'Online')
            OR
            (store_type = 'physical' AND city IN ('Stockholm', 'Uppsala', 'Göteborg'))
        )
);


CREATE TABLE products (
    product_id TEXT PRIMARY KEY,

    supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,

    base_price_sek NUMERIC(12, 2) NOT NULL CHECK (base_price_sek >= 0),
    base_cost_sek NUMERIC(12, 2) NOT NULL CHECK (base_cost_sek >= 0),

    launch_date DATE NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT chk_product_cost_below_price
        CHECK (base_cost_sek <= base_price_sek)
);


CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,

    order_date DATE NOT NULL,

    store_id TEXT NOT NULL REFERENCES stores(store_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    order_status TEXT NOT NULL CHECK (
        order_status IN ('completed', 'cancelled')
    ),

    payment_method TEXT NOT NULL CHECK (
        payment_method IN ('card', 'swish', 'klarna', 'gift_card')
    )
);


CREATE TABLE order_items (
    order_item_id TEXT PRIMARY KEY,

    order_id TEXT NOT NULL REFERENCES orders(order_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    product_id TEXT NOT NULL REFERENCES products(product_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    quantity INTEGER NOT NULL CHECK (quantity > 0),

    unit_price_sek NUMERIC(12, 2) NOT NULL CHECK (unit_price_sek >= 0),
    unit_cost_sek NUMERIC(12, 2) NOT NULL CHECK (unit_cost_sek >= 0),

    discount_amount_sek NUMERIC(12, 2) NOT NULL DEFAULT 0
        CHECK (discount_amount_sek >= 0),

    CONSTRAINT chk_order_item_cost_below_price
        CHECK (unit_cost_sek <= unit_price_sek),

    CONSTRAINT chk_order_item_discount_not_above_gross
        CHECK (discount_amount_sek <= quantity * unit_price_sek)
);


-- ─────────────────────────────────────────────────────────────────────────────
-- Indexes
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX idx_orders_order_date
    ON orders(order_date);

CREATE INDEX idx_orders_store_id
    ON orders(store_id);

CREATE INDEX idx_products_supplier_id
    ON products(supplier_id);

CREATE INDEX idx_products_category
    ON products(category);

CREATE INDEX idx_order_items_order_id
    ON order_items(order_id);

CREATE INDEX idx_order_items_product_id
    ON order_items(product_id);