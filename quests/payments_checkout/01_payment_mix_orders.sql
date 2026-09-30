
-- Question: What is the payment type mix by order count?

SELECT payment_type, COUNT(DISTINCT order_id) AS orders
FROM order_payments
GROUP BY payment_type
ORDER BY orders DESC;
