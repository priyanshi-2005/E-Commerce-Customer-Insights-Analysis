
-- Question: What categories do top sellers focus on?
-- Top 10 sellers by revenue

WITH top_sellers AS (
    SELECT seller_id
    FROM (
        SELECT seller_id, SUM(item_gmv) AS revenue
        FROM v_item_enriched
        GROUP BY seller_id
        ORDER BY revenue DESC
        LIMIT 10
    )
)
SELECT
    ie.category,
    ROUND(SUM(ie.item_gmv), 2) AS revenue
FROM v_item_enriched ie
JOIN top_sellers ts ON ie.seller_id = ts.seller_id
GROUP BY ie.category
ORDER BY revenue DESC
LIMIT 15;
