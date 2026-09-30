-- Latest quarter vs prior quarter category growth.
WITH cat AS (
    SELECT
        category,
        SUM(CASE WHEN purchase_month BETWEEN '2018-03' AND '2018-05' THEN item_gmv ELSE 0 END) AS prior_gmv,
        SUM(CASE WHEN purchase_month BETWEEN '2018-06' AND '2018-08' THEN item_gmv ELSE 0 END) AS recent_gmv
    FROM v_item_enriched
    GROUP BY category
)
SELECT
    category,
    ROUND(prior_gmv, 2) AS prior_gmv,
    ROUND(recent_gmv, 2) AS recent_gmv,
    ROUND((recent_gmv - prior_gmv) * 100.0 / NULLIF(prior_gmv, 0), 2) AS growth_pct
FROM cat
WHERE prior_gmv >= 8000
ORDER BY growth_pct DESC
LIMIT 12;
