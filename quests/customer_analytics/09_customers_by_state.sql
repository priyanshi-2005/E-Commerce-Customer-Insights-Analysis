
-- Question: Which states have the most customers?

SELECT
    customer_state,
    COUNT(DISTINCT customer_unique_id) AS customers
FROM v_item_enriched
GROUP BY customer_state
ORDER BY customers DESC;
