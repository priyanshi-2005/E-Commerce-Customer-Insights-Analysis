
-- Question: Do high-value orders prefer credit card?
-- Top quartile orders by GMV

WITH ranked AS (
    SELECT order_id, order_gmv,
        NTILE(4) OVER (ORDER BY order_gmv DESC) AS quartile
    FROM v_order_revenue
),
threshold AS (
    SELECT ROUND(MIN(order_gmv), 2) AS gmv_threshold FROM ranked WHERE quartile = 1
),
high AS (
    SELECT order_id FROM ranked WHERE quartile = 1
),
stats AS (
    SELECT
        COUNT(DISTINCT h.order_id) AS high_orders,
        COUNT(DISTINCT CASE WHEN op.payment_type = 'credit_card' THEN h.order_id END) AS cc_orders
    FROM high h
    LEFT JOIN order_payments op ON h.order_id = op.order_id
)
SELECT
    'top_quartile' AS order_value_tier,
    (SELECT gmv_threshold FROM threshold) AS gmv_threshold,
    ROUND((SELECT cc_orders FROM stats) * 100.0 / NULLIF((SELECT high_orders FROM stats), 0), 2) AS credit_card_share_pct;
