
-- Question: Which categories underperform on revenue share?

WITH cat AS (
    SELECT category, ROUND(SUM(item_gmv), 2) AS revenue
    FROM v_item_enriched
    GROUP BY category
),
tot AS (SELECT SUM(revenue) AS total_revenue FROM cat)
SELECT
    category,
    revenue,
    ROUND(revenue * 100.0 / (SELECT total_revenue FROM tot), 2) AS revenue_share_pct
FROM cat
ORDER BY revenue_share_pct ASC
LIMIT 15;
