
-- Question: Which categories have the highest AOV?
-- Average item GMV by category

SELECT
    category,
    ROUND(AVG(item_gmv), 2) AS avg_order_value
FROM v_item_enriched
GROUP BY category
ORDER BY avg_order_value DESC
LIMIT 15;
