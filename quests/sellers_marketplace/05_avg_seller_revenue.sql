
-- Question: What is the average revenue per seller?

WITH seller_rev AS (
    SELECT seller_id, SUM(item_gmv) AS revenue
    FROM v_item_enriched
    GROUP BY seller_id
)
SELECT
    CASE
        WHEN revenue < 1000 THEN '< R$1k'
        WHEN revenue < 5000 THEN 'R$1k-5k'
        WHEN revenue < 20000 THEN 'R$5k-20k'
        WHEN revenue < 50000 THEN 'R$20k-50k'
        ELSE 'R$50k+'
    END AS revenue_bucket,
    COUNT(*) AS sellers,
    ROUND(AVG(revenue), 2) AS revenue
FROM seller_rev
GROUP BY revenue_bucket
ORDER BY MIN(revenue);
