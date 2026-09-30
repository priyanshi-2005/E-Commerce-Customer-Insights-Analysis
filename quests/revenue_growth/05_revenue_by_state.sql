
-- Question: Which states generate the most revenue?
-- Grain: one row per customer state

WITH state_rev AS (
    SELECT
        c.customer_state,
        ROUND(SUM(v.order_gmv), 2) AS revenue
    FROM v_order_revenue v
    JOIN orders o ON v.order_id = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY c.customer_state
),
tot AS (
    SELECT SUM(revenue) AS total_revenue FROM state_rev
)
SELECT
    customer_state,
    revenue,
    ROUND(revenue * 100.0 / (SELECT total_revenue FROM tot), 2) AS revenue_share_pct
FROM state_rev
ORDER BY revenue DESC;
