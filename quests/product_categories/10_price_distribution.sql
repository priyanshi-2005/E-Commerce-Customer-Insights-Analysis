
-- Question: What is the price distribution by category?
-- Median item price per category

WITH ranked AS (
    SELECT
        category,
        price,
        ROW_NUMBER() OVER (PARTITION BY category ORDER BY price) AS rn,
        COUNT(*) OVER (PARTITION BY category) AS cnt
    FROM v_item_enriched
)
SELECT
    category,
    ROUND(AVG(price), 2) AS median_price
FROM ranked
WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
GROUP BY category
ORDER BY median_price DESC
LIMIT 15;
