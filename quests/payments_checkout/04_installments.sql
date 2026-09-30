
-- Question: How are installment plans distributed?
-- Uses max installments per order

WITH per_order AS (
    SELECT order_id, MAX(payment_installments) AS payment_installments
    FROM order_payments
    GROUP BY order_id
)
SELECT
    payment_installments,
    COUNT(*) AS orders,
    ROUND(AVG(payment_installments * 1.0), 2) AS avg_installments
FROM per_order
GROUP BY payment_installments
ORDER BY payment_installments;
