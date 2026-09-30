-- Checkout approval conversion by payment type. Join.
SELECT
    op.payment_type,
    COUNT(DISTINCT o.order_id) AS orders,
    COUNT(DISTINCT CASE WHEN o.order_approved_at IS NOT NULL THEN o.order_id END) AS approved_orders,
    ROUND(
        COUNT(DISTINCT CASE WHEN o.order_approved_at IS NOT NULL THEN o.order_id END) * 100.0
        / COUNT(DISTINCT o.order_id),
        2
    ) AS approval_rate_pct
FROM orders o
JOIN order_payments op ON o.order_id = op.order_id
WHERE strftime('%Y-%m', o.order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
GROUP BY op.payment_type
ORDER BY orders DESC;
