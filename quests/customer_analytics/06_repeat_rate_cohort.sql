
-- Question: What is repeat purchase rate by first-order cohort?

WITH first_order AS (
    SELECT customer_unique_id, MIN(purchase_month) AS cohort_month
    FROM v_order_revenue
    GROUP BY customer_unique_id
),
cohort_stats AS (
    SELECT
        f.cohort_month,
        COUNT(*) AS cohort_customers,
        SUM(CASE WHEN c.total_orders > 1 THEN 1 ELSE 0 END) AS repeat_customers
    FROM first_order f
    JOIN v_customer_orders c ON f.customer_unique_id = c.customer_unique_id
    GROUP BY f.cohort_month
)
SELECT
    cohort_month,
    repeat_customers,
    ROUND(repeat_customers * 100.0 / cohort_customers, 2) AS repeat_rate_pct
FROM cohort_stats
ORDER BY cohort_month;
