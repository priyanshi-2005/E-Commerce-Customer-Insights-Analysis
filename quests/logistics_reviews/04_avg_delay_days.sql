
-- Question: How many days late are deliveries on average?
-- Only late orders; average by customer state

WITH late AS (
    SELECT
        o.order_id,
        c.customer_state,
        CAST(
            julianday(o.order_delivered_customer_date) - julianday(o.order_estimated_delivery_date)
        AS INTEGER) AS delay_days
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
      AND julianday(o.order_delivered_customer_date) > julianday(o.order_estimated_delivery_date)
)
SELECT
    customer_state,
    COUNT(*) AS orders,
    ROUND(AVG(delay_days * 1.0), 2) AS avg_delay_days
FROM late
GROUP BY customer_state
HAVING COUNT(*) >= 50
ORDER BY avg_delay_days DESC
LIMIT 20;
