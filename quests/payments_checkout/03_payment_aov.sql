
-- Question: Which payment types have the highest AOV?
-- Primary payment type per order (highest payment_value)

WITH primary_pay AS (
    SELECT order_id, payment_type
    FROM (
        SELECT
            order_id,
            payment_type,
            ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY payment_value DESC) AS rn
        FROM order_payments
    )
    WHERE rn = 1
)
SELECT
    pp.payment_type,
    ROUND(AVG(v.order_gmv), 2) AS avg_order_value
FROM primary_pay pp
JOIN v_order_revenue v ON pp.order_id = v.order_id
GROUP BY pp.payment_type
ORDER BY avg_order_value DESC;
