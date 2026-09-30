WITH flags AS (
    SELECT
        o.order_id,
        c.customer_unique_id,
        c.customer_state,
        strftime('%Y-%m', o.order_purchase_timestamp) AS purchase_month,
        COALESCE(g.order_gmv, 0) AS order_gmv,
        CASE WHEN o.order_delivered_customer_date IS NOT NULL THEN 1 ELSE 0 END AS is_delivered,
        CASE
            WHEN o.order_delivered_carrier_date IS NOT NULL
              OR o.order_delivered_customer_date IS NOT NULL THEN 1
            ELSE 0
        END AS is_shipped,
        CASE
            WHEN o.order_approved_at IS NOT NULL
              OR o.order_delivered_carrier_date IS NOT NULL
              OR o.order_delivered_customer_date IS NOT NULL THEN 1
            ELSE 0
        END AS is_approved
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN v_order_revenue g ON o.order_id = g.order_id
    WHERE strftime('%Y-%m', o.order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
)

SELECT
    customer_state,
    COUNT(*) AS orders,
    ROUND(SUM(CASE WHEN is_delivered = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS dropoff_pct,
    ROUND(SUM(CASE WHEN is_delivered = 0 THEN order_gmv ELSE 0 END), 2) AS gmv_lost
FROM flags
GROUP BY customer_state
HAVING COUNT(*) >= 300
ORDER BY dropoff_pct DESC
LIMIT 12;
