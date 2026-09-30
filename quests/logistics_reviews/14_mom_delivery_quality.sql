-- Delivery conversion and on-time rate by month.
WITH monthly AS (
    SELECT
        strftime('%Y-%m', order_purchase_timestamp) AS purchase_month,
        AVG(CASE WHEN order_delivered_customer_date IS NOT NULL THEN 1.0 ELSE 0 END) AS delivery_conversion,
        AVG(
            CASE
                WHEN order_delivered_customer_date IS NULL THEN NULL
                WHEN julianday(order_delivered_customer_date) - julianday(order_estimated_delivery_date) <= 0 THEN 1.0
                ELSE 0
            END
        ) AS on_time
    FROM orders
    WHERE strftime('%Y-%m', order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
    GROUP BY purchase_month
)
SELECT
    purchase_month,
    ROUND(delivery_conversion * 100, 2) AS delivery_conversion_pct,
    ROUND(on_time * 100, 2) AS on_time_pct
FROM monthly
ORDER BY purchase_month;
