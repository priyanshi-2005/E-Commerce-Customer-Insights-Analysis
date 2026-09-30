
-- Question: Which categories get the most orders?
-- Distinct order_id per category

SELECT
    category,
    COUNT(DISTINCT order_id) AS orders
FROM v_item_enriched
GROUP BY category
ORDER BY orders DESC
LIMIT 15;
