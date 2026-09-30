
-- Question: What is freight revenue by category?

SELECT
    category,
    ROUND(SUM(freight_value), 2) AS freight_revenue
FROM v_item_enriched
GROUP BY category
ORDER BY freight_revenue DESC
LIMIT 15;
