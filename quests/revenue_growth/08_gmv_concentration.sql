
-- Question: What share of GMV comes from the top 10% of orders?
-- Top decile by order GMV vs remainder

WITH ranked AS (
    SELECT
        order_id,
        order_gmv,
        NTILE(10) OVER (ORDER BY order_gmv DESC) AS decile
    FROM v_order_revenue
),
segmented AS (
    SELECT
        CASE WHEN decile = 1 THEN 'top_10_pct_orders' ELSE 'other_90_pct_orders' END AS segment,
        SUM(order_gmv) AS gmv
    FROM ranked
    GROUP BY 1
),
tot AS (
    SELECT SUM(order_gmv) AS total_gmv, COUNT(*) AS total_orders FROM v_order_revenue
)
SELECT
    s.segment,
    ROUND(s.gmv, 2) AS gmv,
    ROUND(
        (SELECT gmv FROM segmented WHERE segment = 'top_10_pct_orders') * 100.0
        / (SELECT total_gmv FROM tot),
        2
    ) AS top_decile_gmv_share_pct,
    ROUND((SELECT total_gmv FROM tot), 2) AS total_gmv,
    (SELECT total_orders FROM tot) AS total_orders
FROM segmented s
ORDER BY CASE s.segment WHEN 'top_10_pct_orders' THEN 1 ELSE 2 END;
