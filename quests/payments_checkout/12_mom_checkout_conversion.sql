-- Month-over-month purchase-to-approval conversion.
WITH monthly AS (
    SELECT
        strftime('%Y-%m', order_purchase_timestamp) AS purchase_month,
        COUNT(*) AS orders,
        SUM(CASE WHEN order_approved_at IS NOT NULL THEN 1 ELSE 0 END) AS approved_orders
    FROM orders
    WHERE strftime('%Y-%m', order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
    GROUP BY purchase_month
)
SELECT
    purchase_month,
    orders,
    approved_orders,
    ROUND(approved_orders * 100.0 / orders, 2) AS conversion_pct,
    ROUND(
        approved_orders * 100.0 / orders
        - LAG(approved_orders * 100.0 / orders) OVER (ORDER BY purchase_month),
        2
    ) AS conversion_change_pct
FROM monthly
ORDER BY purchase_month;
