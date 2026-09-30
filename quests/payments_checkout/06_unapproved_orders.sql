
-- Question: What share of orders never get approved?

SELECT
    purchase_month,
    COUNT(*) AS orders,
    ROUND(
        SUM(CASE WHEN o.order_approved_at IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    ) AS unapproved_rate_pct
FROM v_order_revenue v
JOIN orders o ON v.order_id = o.order_id
GROUP BY purchase_month
ORDER BY purchase_month;
