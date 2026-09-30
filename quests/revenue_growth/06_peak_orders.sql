
-- Question: Which month had the highest order volume?
-- Grain: one row per purchase month

SELECT
    purchase_month,
    COUNT(DISTINCT order_id) AS orders,
    ROUND(SUM(order_gmv), 2) AS gmv
FROM v_order_revenue
GROUP BY purchase_month
ORDER BY purchase_month;
