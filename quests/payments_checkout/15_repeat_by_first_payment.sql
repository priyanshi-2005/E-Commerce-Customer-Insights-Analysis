-- Which first payment type is followed by a second order?
-- Window: ROW_NUMBER. Grain: customer_unique_id.
WITH first_order AS (
    SELECT
        customer_unique_id,
        order_id,
        ROW_NUMBER() OVER (
            PARTITION BY customer_unique_id
            ORDER BY order_purchase_timestamp
        ) AS rn
    FROM v_order_revenue
),
first_pay AS (
    SELECT
        f.customer_unique_id,
        op.payment_type,
        CASE WHEN c.total_orders > 1 THEN 1 ELSE 0 END AS did_repeat
    FROM first_order f
    JOIN order_payments op ON f.order_id = op.order_id AND op.payment_sequential = 1
    JOIN v_customer_orders c ON f.customer_unique_id = c.customer_unique_id
    WHERE f.rn = 1
)
SELECT
    payment_type,
    COUNT(*) AS customers,
    SUM(did_repeat) AS repeat_customers,
    ROUND(AVG(did_repeat) * 100, 2) AS repeat_rate_pct
FROM first_pay
GROUP BY payment_type
HAVING COUNT(*) >= 50
ORDER BY customers DESC;
