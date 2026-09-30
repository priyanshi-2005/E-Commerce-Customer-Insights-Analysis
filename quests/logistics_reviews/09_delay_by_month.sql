
-- Question: Which months had the worst delivery delays?

WITH late AS (
    SELECT
        strftime('%Y-%m', order_purchase_timestamp) AS purchase_month,
        CAST(
            julianday(order_delivered_customer_date) - julianday(order_estimated_delivery_date)
        AS INTEGER) AS delay_days
    FROM orders
    WHERE order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
      AND julianday(order_delivered_customer_date) > julianday(order_estimated_delivery_date)
)
SELECT
    purchase_month,
    COUNT(*) AS late_orders,
    ROUND(AVG(delay_days * 1.0), 2) AS avg_delay_days
FROM late
GROUP BY purchase_month
ORDER BY purchase_month;
