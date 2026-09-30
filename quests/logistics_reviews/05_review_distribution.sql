
-- Question: What is the review score distribution?

WITH scores AS (
    SELECT review_score, COUNT(*) AS reviews
    FROM order_reviews
    WHERE review_score IS NOT NULL
    GROUP BY review_score
),
tot AS (SELECT SUM(reviews) AS total FROM scores)
SELECT
    review_score,
    reviews,
    ROUND(reviews * 100.0 / (SELECT total FROM tot), 2) AS share_pct
FROM scores
ORDER BY review_score;
