
-- Question: Does late delivery hurt review scores?

WITH delivery AS (
    SELECT
        o.order_id,
        CAST(
            julianday(o.order_delivered_customer_date) - julianday(o.order_estimated_delivery_date)
        AS INTEGER) AS delay_days,
        r.review_score
    FROM orders o
    JOIN order_reviews r ON o.order_id = r.order_id
    WHERE o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
      AND r.review_score IS NOT NULL
)
SELECT
    CASE
        WHEN delay_days <= 0 THEN 'on_time_or_early'
        WHEN delay_days BETWEEN 1 AND 3 THEN 'slight_delay'
        WHEN delay_days BETWEEN 4 AND 7 THEN 'moderate_delay'
        ELSE 'severe_delay'
    END AS delay_bucket,
    COUNT(*) AS reviews,
    ROUND(AVG(review_score), 2) AS avg_review_score
FROM delivery
GROUP BY delay_bucket
ORDER BY avg_review_score DESC;
