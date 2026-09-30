-- Repeat purchase rate by category. Grain: customer_unique_id.
WITH cust_cat AS (
    SELECT category, customer_unique_id, COUNT(DISTINCT order_id) AS orders
    FROM v_item_enriched
    WHERE purchase_month BETWEEN '2017-01' AND '2018-08'
    GROUP BY category, customer_unique_id
)
SELECT
    category,
    COUNT(*) AS customers,
    SUM(CASE WHEN orders > 1 THEN 1 ELSE 0 END) AS repeat_customers,
    ROUND(SUM(CASE WHEN orders > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS repeat_rate_pct
FROM cust_cat
GROUP BY category
HAVING COUNT(*) >= 400
ORDER BY repeat_rate_pct DESC
LIMIT 12;
