
-- Question: What is the on-time delivery rate?

WITH delivered AS (
    SELECT
        order_id,
        CAST(
            julianday(order_delivered_customer_date) - julianday(order_estimated_delivery_date)
        AS INTEGER) AS delay_days
    FROM orders
    WHERE order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
),
tagged AS (
    SELECT
        CASE WHEN delay_days <= 0 THEN 'On Time' ELSE 'Late' END AS delivery_result,
        order_id,
        delay_days
    FROM delivered
),
tot AS (
    SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN delay_days > 0 THEN 1 ELSE 0 END) AS late_deliveries
    FROM delivered
)
SELECT
    t.delivery_result,
    COUNT(*) AS orders,
    ROUND((SELECT SUM(CASE WHEN delay_days <= 0 THEN 1 ELSE 0 END) FROM delivered) * 100.0 / (SELECT total FROM tot), 2) AS on_time_rate_pct,
    (SELECT late_deliveries FROM tot) AS late_deliveries
FROM tagged t
GROUP BY t.delivery_result
ORDER BY t.delivery_result;
