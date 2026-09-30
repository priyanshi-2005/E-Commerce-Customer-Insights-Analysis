
-- Question: How does cohort retention decay over months?

WITH first_order AS (
    SELECT customer_unique_id, MIN(purchase_date) AS first_date
    FROM v_order_revenue
    GROUP BY customer_unique_id
),
activity AS (
    SELECT
        f.customer_unique_id,
        f.first_date,
        CAST(
            (strftime('%Y', v.purchase_date) - strftime('%Y', f.first_date)) * 12
            + (strftime('%m', v.purchase_date) - strftime('%m', f.first_date))
        AS INTEGER) AS months_since_first_order
    FROM first_order f
    JOIN v_order_revenue v ON v.customer_unique_id = f.customer_unique_id
),
cohort_sizes AS (
    SELECT strftime('%Y-%m', first_date) AS cohort_month, COUNT(*) AS cohort_size
    FROM first_order
    GROUP BY cohort_month
),
ret AS (
    SELECT
        strftime('%Y-%m', fo.first_date) AS cohort_month,
        a.months_since_first_order,
        COUNT(DISTINCT a.customer_unique_id) AS active_customers
    FROM activity a
    JOIN first_order fo ON a.customer_unique_id = fo.customer_unique_id
    GROUP BY cohort_month, a.months_since_first_order
)
SELECT
    r.months_since_first_order,
    ROUND(AVG(r.active_customers * 100.0 / cs.cohort_size), 2) AS retention_pct
FROM ret r
JOIN cohort_sizes cs ON r.cohort_month = cs.cohort_month
WHERE r.months_since_first_order >= 0
GROUP BY r.months_since_first_order
ORDER BY r.months_since_first_order;
