
-- Question: How do order count and GMV correlate monthly?
-- Pearson correlation across monthly aggregates

WITH monthly AS (
    SELECT
        purchase_month,
        COUNT(DISTINCT order_id) AS orders,
        SUM(order_gmv) AS gmv
    FROM v_order_revenue
    GROUP BY purchase_month
),
stats AS (
    SELECT
        AVG(orders * 1.0) AS mean_o,
        AVG(gmv) AS mean_g,
        AVG(orders * orders * 1.0) AS mean_o2,
        AVG(gmv * gmv) AS mean_g2,
        AVG(orders * gmv * 1.0) AS mean_og
    FROM monthly
)
SELECT
    m.purchase_month,
    m.orders,
    ROUND(m.gmv, 2) AS gmv,
    ROUND(
        (s.mean_og - s.mean_o * s.mean_g)
        / NULLIF(
            SQRT(s.mean_o2 - s.mean_o * s.mean_o)
            * SQRT(s.mean_g2 - s.mean_g * s.mean_g),
            0
        ),
        4
    ) AS orders_gmv_corr
FROM monthly m
CROSS JOIN stats s
ORDER BY m.purchase_month;
