
-- Question: How many orders use multiple payment methods?

WITH pay_counts AS (
    SELECT order_id, COUNT(*) AS payment_rows
    FROM order_payments
    GROUP BY order_id
),
tagged AS (
    SELECT
        CASE WHEN payment_rows > 1 THEN 'Multi Payment' ELSE 'Single Payment' END AS payment_pattern,
        order_id
    FROM pay_counts
),
tot AS (SELECT COUNT(*) AS total_orders FROM pay_counts)
SELECT
    payment_pattern,
    COUNT(*) AS orders,
    (SELECT SUM(CASE WHEN payment_rows > 1 THEN 1 ELSE 0 END) FROM pay_counts) AS multi_payment_orders,
    ROUND(
        (SELECT SUM(CASE WHEN payment_rows > 1 THEN 1 ELSE 0 END) FROM pay_counts) * 100.0
        / (SELECT total_orders FROM tot),
        2
    ) AS multi_payment_share_pct
FROM tagged
GROUP BY payment_pattern
ORDER BY payment_pattern;
