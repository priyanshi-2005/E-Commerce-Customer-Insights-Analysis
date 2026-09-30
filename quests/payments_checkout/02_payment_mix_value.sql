
-- Question: What is the payment type mix by value?

WITH by_type AS (
    SELECT payment_type, ROUND(SUM(payment_value), 2) AS total_payment_value
    FROM order_payments
    GROUP BY payment_type
),
tot AS (SELECT SUM(total_payment_value) AS total FROM by_type)
SELECT
    payment_type,
    total_payment_value,
    ROUND(total_payment_value * 100.0 / (SELECT total FROM tot), 2) AS value_share_pct
FROM by_type
ORDER BY total_payment_value DESC;
