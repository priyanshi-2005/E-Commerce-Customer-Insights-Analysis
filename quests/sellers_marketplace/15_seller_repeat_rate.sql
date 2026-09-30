-- Which sellers bring the same customer back? Grain: customer_unique_id.
WITH seller_cust AS (
    SELECT
        oi.seller_id,
        s.seller_city,
        c.customer_unique_id,
        COUNT(DISTINCT oi.order_id) AS orders
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN sellers s ON oi.seller_id = s.seller_id
    WHERE strftime('%Y-%m', o.order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
    GROUP BY oi.seller_id, s.seller_city, c.customer_unique_id
)
SELECT
    seller_city || ' · ' || substr(seller_id, 1, 8) AS seller_label,
    COUNT(*) AS customers,
    ROUND(SUM(CASE WHEN orders > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS repeat_rate_pct
FROM seller_cust
GROUP BY seller_id, seller_city
HAVING COUNT(*) >= 100
ORDER BY repeat_rate_pct DESC
LIMIT 12;
