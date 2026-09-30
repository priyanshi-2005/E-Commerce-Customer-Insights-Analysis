
-- Question: What is the month-over-month GMV growth rate?
-- Grain: one row per month; first month has NULL mom_growth_pct

WITH monthly AS (
    SELECT
        purchase_month,
        ROUND(SUM(order_gmv), 2) AS gmv
    FROM v_order_revenue
    GROUP BY purchase_month
),
with_lag AS (
    SELECT
        purchase_month,
        gmv,
        LAG(gmv) OVER (ORDER BY purchase_month) AS prev_gmv
    FROM monthly
)
SELECT
    purchase_month,
    gmv,
    ROUND(
        CASE
            WHEN prev_gmv IS NULL OR prev_gmv = 0 THEN NULL
            ELSE (gmv - prev_gmv) * 100.0 / prev_gmv
        END,
        2
    ) AS mom_growth_pct
FROM with_lag
ORDER BY purchase_month;
