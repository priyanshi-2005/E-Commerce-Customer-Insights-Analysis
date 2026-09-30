-- New vs repeat GMV. Grain: customer_unique_id. Join + CTE.
WITH firsts AS (
    SELECT customer_unique_id, MIN(purchase_month) AS first_month
    FROM v_order_revenue
    GROUP BY customer_unique_id
)
SELECT
    v.purchase_month,
    ROUND(SUM(CASE WHEN v.purchase_month = f.first_month THEN v.order_gmv ELSE 0 END), 2) AS new_gmv,
    ROUND(SUM(CASE WHEN v.purchase_month > f.first_month THEN v.order_gmv ELSE 0 END), 2) AS repeat_gmv,
    ROUND(
        SUM(CASE WHEN v.purchase_month > f.first_month THEN v.order_gmv ELSE 0 END) * 100.0
        / SUM(v.order_gmv),
        2
    ) AS repeat_share_pct
FROM v_order_revenue v
JOIN firsts f ON v.customer_unique_id = f.customer_unique_id
WHERE v.purchase_month BETWEEN '2017-01' AND '2018-08'
GROUP BY v.purchase_month
ORDER BY v.purchase_month;
