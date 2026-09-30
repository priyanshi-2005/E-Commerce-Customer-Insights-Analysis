
-- Question: What is average payment value by type and month?
-- Overall avg payment value per month (all types)

SELECT
    strftime('%Y-%m', o.order_purchase_timestamp) AS purchase_month,
    op.payment_type,
    ROUND(AVG(op.payment_value), 2) AS avg_payment_value
FROM order_payments op
JOIN orders o ON op.order_id = o.order_id
GROUP BY purchase_month, op.payment_type
ORDER BY purchase_month, op.payment_type;
