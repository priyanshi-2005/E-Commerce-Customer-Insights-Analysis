
-- Question: Is credit card share increasing over time?

WITH monthly AS (
    SELECT
        v.purchase_month,
        COUNT(DISTINCT v.order_id) AS total_orders,
        COUNT(DISTINCT CASE WHEN op.payment_type = 'credit_card' THEN op.order_id END) AS cc_orders
    FROM v_order_revenue v
    LEFT JOIN order_payments op ON v.order_id = op.order_id
    GROUP BY v.purchase_month
)
SELECT
    purchase_month,
    cc_orders,
    total_orders,
    ROUND(cc_orders * 100.0 / NULLIF(total_orders, 0), 2) AS credit_card_share_pct
FROM monthly
ORDER BY purchase_month;
