-- Sellers with the most GMV stuck before delivery.
WITH seller_orders AS (
    SELECT
        oi.seller_id,
        s.seller_city,
        oi.order_id,
        MAX(CASE WHEN o.order_delivered_customer_date IS NULL THEN 1 ELSE 0 END) AS dropped,
        SUM(oi.price + oi.freight_value) AS gmv
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN sellers s ON oi.seller_id = s.seller_id
    WHERE strftime('%Y-%m', o.order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
    GROUP BY oi.seller_id, s.seller_city, oi.order_id
)
SELECT
    seller_city || ' · ' || substr(seller_id, 1, 8) AS seller_label,
    COUNT(*) AS orders,
    ROUND(AVG(dropped) * 100, 2) AS dropoff_pct,
    ROUND(SUM(CASE WHEN dropped = 1 THEN gmv ELSE 0 END), 2) AS gmv_lost
FROM seller_orders
GROUP BY seller_id, seller_city
HAVING COUNT(*) >= 80
ORDER BY gmv_lost DESC
LIMIT 12;
