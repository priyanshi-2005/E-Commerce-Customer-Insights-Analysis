
-- Question: How many customers have not ordered in 6+ months?
-- Churn proxy: no order in 180 days before max purchase date

WITH bounds AS (
    SELECT MAX(purchase_date) AS max_date FROM v_order_revenue
),
last_active AS (
    SELECT customer_unique_id, MAX(purchase_date) AS last_order_date
    FROM v_order_revenue
    GROUP BY customer_unique_id
),
tagged AS (
    SELECT
        customer_unique_id,
        CASE
            WHEN julianday((SELECT max_date FROM bounds)) - julianday(last_order_date) > 180
            THEN 'Churned Proxy'
            ELSE 'Active'
        END AS status
    FROM last_active
),
tot AS (SELECT COUNT(*) AS total FROM tagged)
SELECT
    status,
    COUNT(*) AS customers,
    ROUND(
        SUM(CASE WHEN status = 'Churned Proxy' THEN 1 ELSE 0 END) * 100.0 / (SELECT total FROM tot),
        2
    ) AS churn_rate_pct
FROM tagged
GROUP BY status
ORDER BY CASE status WHEN 'Churned Proxy' THEN 1 ELSE 2 END;
