-- High-value customers (top 20%) split by how recently they ordered.
-- Retention target: 91+ day buckets.

WITH bounds AS (
    SELECT MAX(DATE(order_purchase_timestamp)) AS snapshot_date
    FROM orders
    WHERE strftime('%Y-%m', order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
),
base AS (
    SELECT
        c.customer_unique_id,
        CAST(
            julianday((SELECT snapshot_date FROM bounds))
            - julianday(MAX(DATE(o.order_purchase_timestamp)))
        AS INTEGER) AS recency_days,
        COUNT(DISTINCT o.order_id) AS frequency,
        SUM(oi.price + oi.freight_value) AS monetary
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE strftime('%Y-%m', o.order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
    GROUP BY c.customer_unique_id
),
scored AS (
    SELECT
        customer_unique_id,
        recency_days,
        frequency,
        monetary,
        NTILE(5) OVER (ORDER BY recency_days DESC, customer_unique_id) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC, customer_unique_id) AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC, customer_unique_id) AS m_score
    FROM base
),
rfm AS (
    SELECT
        customer_unique_id,
        recency_days,
        frequency,
        monetary,
        r_score,
        f_score,
        m_score,
        (r_score + f_score + m_score) AS rfm_score,
        CASE WHEN m_score = 5 THEN 1 ELSE 0 END AS is_top20
    FROM scored
)

SELECT
    CASE
        WHEN recency_days <= 30 THEN '0-30 days active'
        WHEN recency_days <= 90 THEN '31-90 days watch'
        WHEN recency_days <= 180 THEN '91-180 days at risk'
        ELSE '180+ days lapsed'
    END AS recency_bucket,
    COUNT(*) AS customers,
    ROUND(SUM(monetary), 2) AS gmv,
    MIN(recency_days) AS bucket_start
FROM rfm
WHERE is_top20 = 1
GROUP BY recency_bucket
ORDER BY bucket_start;
