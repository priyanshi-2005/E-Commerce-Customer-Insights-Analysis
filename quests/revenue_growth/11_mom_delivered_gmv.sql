-- Delivered GMV growth. Window: LAG.
WITH monthly AS (
    SELECT
        purchase_month,
        ROUND(SUM(CASE WHEN order_status = 'delivered' THEN order_gmv ELSE 0 END), 2) AS delivered_gmv
    FROM v_order_revenue
    WHERE purchase_month BETWEEN '2017-01' AND '2018-08'
    GROUP BY purchase_month
)
SELECT
    purchase_month,
    delivered_gmv,
    ROUND(
        (delivered_gmv - LAG(delivered_gmv) OVER (ORDER BY purchase_month)) * 100.0
        / NULLIF(LAG(delivered_gmv) OVER (ORDER BY purchase_month), 0),
        2
    ) AS mom_growth_pct
FROM monthly
ORDER BY purchase_month;
