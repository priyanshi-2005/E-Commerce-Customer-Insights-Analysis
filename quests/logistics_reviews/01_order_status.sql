
-- Question: What is the order status distribution?

WITH status_counts AS (
    SELECT order_status, COUNT(*) AS orders
    FROM orders
    GROUP BY order_status
),
tot AS (SELECT SUM(orders) AS total FROM status_counts)
SELECT
    order_status,
    orders,
    ROUND(orders * 100.0 / (SELECT total FROM tot), 2) AS share_pct
FROM status_counts
ORDER BY orders DESC;
