-- Sellers active last month who sold again. CTE + self-join + LAG.
WITH active AS (
    SELECT DISTINCT
        oi.seller_id,
        strftime('%Y-%m', o.order_purchase_timestamp) AS month
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    WHERE strftime('%Y-%m', o.order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
),
months AS (
    SELECT month, COUNT(*) AS active_sellers
    FROM active
    GROUP BY month
),
retained AS (
    SELECT a.month, COUNT(*) AS retained_sellers
    FROM active a
    JOIN active prev
      ON a.seller_id = prev.seller_id
     AND prev.month = strftime('%Y-%m', date(a.month || '-01', '-1 month'))
    GROUP BY a.month
),
rates AS (
    SELECT
        r.month,
        m_prev.active_sellers,
        r.retained_sellers,
        ROUND(r.retained_sellers * 100.0 / m_prev.active_sellers, 2) AS mom_retention_pct
    FROM retained r
    JOIN months m_prev
      ON m_prev.month = strftime('%Y-%m', date(r.month || '-01', '-1 month'))
    WHERE m_prev.active_sellers >= 100
)
SELECT
    month,
    active_sellers,
    retained_sellers,
    mom_retention_pct,
    ROUND(mom_retention_pct - LAG(mom_retention_pct) OVER (ORDER BY month), 2) AS retention_change_pct
FROM rates
ORDER BY month;
