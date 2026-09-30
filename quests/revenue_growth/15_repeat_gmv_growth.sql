-- Month-over-month growth of repeat-customer revenue. Window: LAG.
WITH firsts AS (
    SELECT customer_unique_id, MIN(purchase_month) AS first_month
    FROM v_order_revenue
    GROUP BY customer_unique_id
),
monthly AS (
    SELECT
        v.purchase_month,
        ROUND(SUM(CASE WHEN v.purchase_month > f.first_month THEN v.order_gmv ELSE 0 END), 2) AS repeat_gmv
    FROM v_order_revenue v
    JOIN firsts f ON v.customer_unique_id = f.customer_unique_id
    WHERE v.purchase_month BETWEEN '2017-01' AND '2018-08'
    GROUP BY v.purchase_month
)
SELECT
    purchase_month,
    repeat_gmv,
    ROUND(
        (repeat_gmv - LAG(repeat_gmv) OVER (ORDER BY purchase_month)) * 100.0
        / NULLIF(LAG(repeat_gmv) OVER (ORDER BY purchase_month), 0),
        2
    ) AS mom_growth_pct
FROM monthly
ORDER BY purchase_month;
