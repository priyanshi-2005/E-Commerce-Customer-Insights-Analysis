
-- Question: Which categories get the lowest review scores?

SELECT
    ie.category,
    COUNT(DISTINCT r.order_id) AS orders,
    ROUND(AVG(r.review_score * 1.0), 2) AS avg_review_score
FROM order_reviews r
JOIN v_item_enriched ie ON r.order_id = ie.order_id
WHERE r.review_score IS NOT NULL
GROUP BY ie.category
HAVING COUNT(DISTINCT r.order_id) >= 100
ORDER BY avg_review_score ASC
LIMIT 15;
