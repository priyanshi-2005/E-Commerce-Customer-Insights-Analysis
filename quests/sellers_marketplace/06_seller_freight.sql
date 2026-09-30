
-- Question: Which sellers have the highest freight charges?

SELECT
    seller_id,
    ROUND(SUM(freight_value), 2) AS freight_revenue
FROM v_item_enriched
GROUP BY seller_id
ORDER BY freight_revenue DESC
LIMIT 15;
