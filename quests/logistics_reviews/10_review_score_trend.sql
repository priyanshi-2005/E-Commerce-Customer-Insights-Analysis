
-- Question: Do review scores trend down over time?

SELECT
    strftime('%Y-%m', review_creation_date) AS review_month,
    COUNT(*) AS reviews,
    ROUND(AVG(review_score * 1.0), 2) AS avg_review_score
FROM order_reviews
WHERE review_score IS NOT NULL
  AND review_creation_date IS NOT NULL
GROUP BY review_month
ORDER BY review_month;
