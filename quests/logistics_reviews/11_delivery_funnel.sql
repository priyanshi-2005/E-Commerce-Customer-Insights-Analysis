-- Delivery drop-off funnel. Windows: LAG, FIRST_VALUE.

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

, stages AS (
    SELECT 1 AS stage_order, 'Purchased' AS stage, COUNT(*) AS orders FROM flags
    UNION ALL
    SELECT 2, 'Approved', COUNT(*) FROM flags WHERE is_approved = 1
    UNION ALL
    SELECT 3, 'Shipped', COUNT(*) FROM flags WHERE is_shipped = 1
    UNION ALL
    SELECT 4, 'Delivered', COUNT(*) FROM flags WHERE is_delivered = 1
),
with_lag AS (
    SELECT
        stage_order,
        stage,
        orders,
        ROUND(orders * 100.0 / FIRST_VALUE(orders) OVER (ORDER BY stage_order), 2) AS conversion_from_start_pct,
        LAG(orders) OVER (ORDER BY stage_order) AS prior_orders
    FROM stages
)
SELECT
    stage,
    orders,
    conversion_from_start_pct,
    ROUND(
        CASE
            WHEN prior_orders IS NULL THEN 0
            ELSE (prior_orders - orders) * 100.0 / prior_orders
        END,
        2
    ) AS dropoff_from_prior_pct
FROM with_lag
ORDER BY stage_order;
