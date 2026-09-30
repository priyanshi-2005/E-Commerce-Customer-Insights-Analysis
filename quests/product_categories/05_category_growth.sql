
-- Question: Which categories grew fastest in the latest 6 months?
-- Compare avg GMV in first vs last 3 months of the 6-month window

WITH bounds AS (
    SELECT MAX(purchase_month) AS max_m FROM v_item_enriched
),
windowed AS (
    SELECT ie.*
    FROM v_item_enriched ie
    CROSS JOIN bounds b
    WHERE ie.purchase_month > strftime('%Y-%m', date(b.max_m || '-01', '-5 months'))
),
monthly_cat AS (
    SELECT category, purchase_month, SUM(item_gmv) AS gmv
    FROM windowed
    GROUP BY category, purchase_month
),
ranked_months AS (
    SELECT DISTINCT purchase_month FROM windowed ORDER BY purchase_month
),
split AS (
    SELECT
        category,
        purchase_month,
        gmv,
        ROW_NUMBER() OVER (ORDER BY purchase_month) AS rn,
        COUNT(*) OVER () AS month_cnt
    FROM monthly_cat
),
periods AS (
    SELECT
        category,
        AVG(CASE WHEN rn <= month_cnt / 2.0 THEN gmv END) AS early_avg,
        AVG(CASE WHEN rn > month_cnt / 2.0 THEN gmv END) AS late_avg
    FROM split
    GROUP BY category
    HAVING early_avg IS NOT NULL AND late_avg IS NOT NULL AND early_avg > 0
)
SELECT
    category,
    ROUND((late_avg - early_avg) * 100.0 / early_avg, 2) AS growth_pct
FROM periods
ORDER BY growth_pct DESC
LIMIT 15;
