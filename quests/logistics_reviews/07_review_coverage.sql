
-- Question: What share of delivered orders get reviewed?

WITH delivered AS (
    SELECT
        order_id,
        strftime('%Y-%m', order_delivered_customer_date) AS month
    FROM orders
    WHERE order_status = 'delivered'
      AND order_delivered_customer_date IS NOT NULL
),
coverage AS (
    SELECT
        d.month,
        COUNT(DISTINCT d.order_id) AS delivered_orders,
        COUNT(DISTINCT r.order_id) AS reviewed_orders
    FROM delivered d
    LEFT JOIN order_reviews r ON d.order_id = r.order_id
    GROUP BY d.month
)
SELECT
    month,
    reviewed_orders,
    delivered_orders,
    ROUND(reviewed_orders * 100.0 / NULLIF(delivered_orders, 0), 2) AS review_coverage_pct
FROM coverage
ORDER BY month;
