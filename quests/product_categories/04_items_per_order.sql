
-- Question: How many items are sold per order by category?

WITH oc AS (
    SELECT category, order_id, COUNT(*) AS items_in_order
    FROM v_item_enriched
    GROUP BY category, order_id
)
SELECT
    category,
    ROUND(AVG(items_in_order * 1.0), 2) AS avg_items_per_order
FROM oc
GROUP BY category
ORDER BY avg_items_per_order DESC
LIMIT 15;
