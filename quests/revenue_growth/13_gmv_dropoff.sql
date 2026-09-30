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
    CASE
        WHEN is_approved = 0 THEN '1. Never approved'
        WHEN is_shipped = 0 THEN '2. Approved, not shipped'
        WHEN is_delivered = 0 THEN '3. Shipped, not delivered'
        ELSE '4. Delivered'
    END AS dropoff_stage,
    COUNT(*) AS orders_lost,
    ROUND(SUM(order_gmv), 2) AS gmv_lost
FROM flags
WHERE is_delivered = 0
GROUP BY dropoff_stage
ORDER BY dropoff_stage;
