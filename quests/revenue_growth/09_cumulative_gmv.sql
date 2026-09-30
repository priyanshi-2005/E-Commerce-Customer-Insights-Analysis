
-- Question: What is the cumulative GMV curve by month?
-- Includes months_to_half on the row where cumulative GMV first reaches 50%

WITH monthly AS (
    SELECT
        purchase_month,
        ROUND(SUM(order_gmv), 2) AS monthly_gmv
    FROM v_order_revenue
    GROUP BY purchase_month
),
cum AS (
    SELECT
        purchase_month,
        monthly_gmv,
        SUM(monthly_gmv) OVER (ORDER BY purchase_month) AS cumulative_gmv,
        SUM(monthly_gmv) OVER () AS total_gmv
    FROM monthly
),
half AS (
    SELECT MIN(purchase_month) AS months_to_half
    FROM cum
    WHERE cumulative_gmv >= total_gmv * 0.5
)
SELECT
    c.purchase_month,
    c.monthly_gmv,
    ROUND(c.cumulative_gmv, 2) AS cumulative_gmv,
    (SELECT COUNT(*) FROM monthly m WHERE m.purchase_month <= (SELECT months_to_half FROM half)) AS months_to_half
FROM cum c
ORDER BY c.purchase_month;
