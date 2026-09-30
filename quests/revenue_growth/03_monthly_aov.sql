
-- Question: How does average order value change monthly?
-- Grain: one row per purchase month

SELECT
    purchase_month,
    ROUND(SUM(order_gmv) * 1.0 / COUNT(DISTINCT order_id), 2) AS avg_order_value
FROM v_order_revenue
GROUP BY purchase_month
ORDER BY purchase_month;
