-- Categories with the worst purchase-to-delivery drop-off.
SELECT
    category,
    COUNT(DISTINCT order_id) AS orders,
    ROUND(
        (COUNT(DISTINCT order_id) - COUNT(DISTINCT CASE WHEN is_delivered = 1 THEN order_id END))
        * 100.0 / COUNT(DISTINCT order_id),
        2
    ) AS dropoff_pct
FROM v_item_enriched
WHERE purchase_month BETWEEN '2017-01' AND '2018-08'
GROUP BY category
HAVING COUNT(DISTINCT order_id) >= 200
ORDER BY dropoff_pct DESC
LIMIT 12;
