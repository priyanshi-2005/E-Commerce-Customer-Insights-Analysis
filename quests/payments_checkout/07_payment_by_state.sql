
-- Question: Which states prefer credit card vs boleto?
-- Top 5 states by order count

WITH top_states AS (
    SELECT customer_state
    FROM (
        SELECT customer_state, COUNT(DISTINCT order_id) AS orders
        FROM v_item_enriched
        GROUP BY customer_state
        ORDER BY orders DESC
        LIMIT 5
    )
)
SELECT
    ie.customer_state,
    op.payment_type,
    COUNT(DISTINCT op.order_id) AS orders
FROM order_payments op
JOIN v_item_enriched ie ON op.order_id = ie.order_id
JOIN top_states ts ON ie.customer_state = ts.customer_state
GROUP BY ie.customer_state, op.payment_type
ORDER BY ie.customer_state, orders DESC;
