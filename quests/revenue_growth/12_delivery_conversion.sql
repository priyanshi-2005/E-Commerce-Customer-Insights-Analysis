-- Purchase-to-delivered conversion by month.
WITH monthly AS (
    SELECT
        strftime('%Y-%m', order_purchase_timestamp) AS purchase_month,
        COUNT(*) AS orders,
        SUM(CASE WHEN order_delivered_customer_date IS NOT NULL THEN 1 ELSE 0 END) AS delivered_orders
    FROM orders
    WHERE strftime('%Y-%m', order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
    GROUP BY purchase_month
)
SELECT
    purchase_month,
    orders,
    delivered_orders,
    ROUND(delivered_orders * 100.0 / orders, 2) AS conversion_pct
FROM monthly
ORDER BY purchase_month;
