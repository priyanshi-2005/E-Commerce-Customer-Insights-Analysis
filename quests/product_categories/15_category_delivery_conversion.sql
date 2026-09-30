-- Order value that actually gets delivered, by category.
WITH cat AS (
    SELECT
        category,
        SUM(item_gmv) AS ordered_gmv,
        SUM(CASE WHEN is_delivered = 1 THEN item_gmv ELSE 0 END) AS delivered_gmv
    FROM v_item_enriched
    WHERE purchase_month BETWEEN '2017-01' AND '2018-08'
    GROUP BY category
)
SELECT
    category,
    ROUND(ordered_gmv, 2) AS ordered_gmv,
    ROUND(delivered_gmv, 2) AS delivered_gmv,
    ROUND(delivered_gmv * 100.0 / NULLIF(ordered_gmv, 0), 2) AS delivery_conversion_pct
FROM cat
WHERE ordered_gmv >= 20000
ORDER BY delivery_conversion_pct ASC
LIMIT 12;
