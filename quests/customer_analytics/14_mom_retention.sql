-- Month-over-month retention: customers active last month who ordered again.
-- Techniques: CTE, self-join, LAG window.
WITH active AS (
    SELECT DISTINCT customer_unique_id, purchase_month AS month
    FROM v_order_revenue
    WHERE purchase_month BETWEEN '2017-01' AND '2018-08'
),
months AS (
    SELECT month, COUNT(*) AS active_customers
    FROM active
    GROUP BY month
),
retained AS (
    SELECT a.month, COUNT(*) AS retained_customers
    FROM active a
    JOIN active prev
      ON a.customer_unique_id = prev.customer_unique_id
     AND prev.month = strftime('%Y-%m', date(a.month || '-01', '-1 month'))
    GROUP BY a.month
),
rates AS (
    SELECT
        r.month,
        m_prev.active_customers AS prior_customers,
        r.retained_customers,
        ROUND(r.retained_customers * 100.0 / m_prev.active_customers, 2) AS mom_retention_pct
    FROM retained r
    JOIN months m_prev
      ON m_prev.month = strftime('%Y-%m', date(r.month || '-01', '-1 month'))
    WHERE m_prev.active_customers >= 500
)
SELECT
    month,
    prior_customers,
    retained_customers,
    mom_retention_pct,
    ROUND(mom_retention_pct - LAG(mom_retention_pct) OVER (ORDER BY month), 2) AS retention_change_pct
FROM rates
ORDER BY month;
