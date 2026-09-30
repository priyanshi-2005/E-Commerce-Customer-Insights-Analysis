
-- Question: Which seller cities dominate GMV?

SELECT
    s.seller_city,
    ROUND(SUM(ie.item_gmv), 2) AS revenue
FROM v_item_enriched ie
JOIN sellers s ON ie.seller_id = s.seller_id
GROUP BY s.seller_city
ORDER BY revenue DESC
LIMIT 15;
