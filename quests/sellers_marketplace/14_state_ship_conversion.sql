-- Shipped-to-delivered conversion by seller state.
WITH seller_orders AS (
    SELECT
        s.seller_state,
        oi.order_id,
        MAX(CASE
            WHEN o.order_delivered_carrier_date IS NOT NULL
              OR o.order_delivered_customer_date IS NOT NULL THEN 1
            ELSE 0
        END) AS shipped,
        MAX(CASE WHEN o.order_delivered_customer_date IS NOT NULL THEN 1 ELSE 0 END) AS delivered
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN sellers s ON oi.seller_id = s.seller_id
    WHERE strftime('%Y-%m', o.order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
    GROUP BY s.seller_state, oi.order_id
)
SELECT
    seller_state,
    SUM(shipped) AS shipped_orders,
    SUM(delivered) AS delivered_orders,
    ROUND(SUM(delivered) * 100.0 / NULLIF(SUM(shipped), 0), 2) AS conversion_pct
FROM seller_orders
GROUP BY seller_state
HAVING SUM(shipped) >= 200
ORDER BY conversion_pct ASC;
