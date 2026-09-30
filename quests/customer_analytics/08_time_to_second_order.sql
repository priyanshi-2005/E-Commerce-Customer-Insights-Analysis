
-- Question: How long until a customer's second order?

WITH ordered AS (
    SELECT
        customer_unique_id,
        order_purchase_timestamp,
        ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY order_purchase_timestamp) AS rn
    FROM v_order_revenue
),
pairs AS (
    SELECT
        CAST(julianday(b.order_purchase_timestamp) - julianday(a.order_purchase_timestamp) AS INTEGER) AS days_to_second
    FROM ordered a
    JOIN ordered b ON a.customer_unique_id = b.customer_unique_id AND b.rn = 2
    WHERE a.rn = 1
),
bucketed AS (
    SELECT
        CASE
            WHEN days_to_second <= 7 THEN '0-7 days'
            WHEN days_to_second <= 30 THEN '8-30 days'
            WHEN days_to_second <= 90 THEN '31-90 days'
            ELSE '90+ days'
        END AS days_bucket,
        days_to_second
    FROM pairs
)
SELECT
    days_bucket,
    COUNT(*) AS customers,
    ROUND(AVG(days_to_second * 1.0), 0) AS days_to_second
FROM bucketed
GROUP BY days_bucket
ORDER BY MIN(days_to_second);
