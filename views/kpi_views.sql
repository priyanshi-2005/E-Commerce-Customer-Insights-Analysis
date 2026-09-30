-- Reusable KPI views for QueryQuest dashboards
-- Customer metrics use customer_unique_id (Olist issues a new customer_id per order).

DROP VIEW IF EXISTS v_rfm_customers;
DROP VIEW IF EXISTS v_customer_orders;
DROP VIEW IF EXISTS v_item_enriched;
DROP VIEW IF EXISTS v_order_revenue;

CREATE VIEW v_order_revenue AS
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    o.order_status,
    o.order_purchase_timestamp,
    DATE(o.order_purchase_timestamp) AS purchase_date,
    strftime('%Y-%m', o.order_purchase_timestamp) AS purchase_month,
    SUM(oi.price + oi.freight_value) AS order_gmv,
    SUM(oi.price) AS product_revenue,
    SUM(oi.freight_value) AS freight_revenue,
    COUNT(DISTINCT oi.product_id) AS distinct_products
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    o.order_status,
    o.order_purchase_timestamp;

CREATE VIEW v_item_enriched AS
SELECT
    oi.order_id,
    oi.order_item_id,
    oi.product_id,
    oi.seller_id,
    oi.price,
    oi.freight_value,
    oi.price + oi.freight_value AS item_gmv,
    COALESCE(ct.product_category_name_english, p.product_category_name, 'unknown') AS category,
    c.customer_id,
    c.customer_unique_id,
    c.customer_city,
    c.customer_state,
    o.order_status,
    o.order_purchase_timestamp,
    strftime('%Y-%m', o.order_purchase_timestamp) AS purchase_month,
    CASE WHEN o.order_delivered_customer_date IS NOT NULL THEN 1 ELSE 0 END AS is_delivered
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN customers c ON o.customer_id = c.customer_id
JOIN products p ON oi.product_id = p.product_id
LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name;

CREATE VIEW v_customer_orders AS
SELECT
    customer_unique_id,
    COUNT(DISTINCT order_id) AS total_orders,
    MIN(purchase_date) AS first_order_date,
    MAX(purchase_date) AS last_order_date,
    SUM(order_gmv) AS lifetime_gmv
FROM v_order_revenue
GROUP BY customer_unique_id;

CREATE INDEX IF NOT EXISTS idx_customers_unique ON customers(customer_unique_id);
