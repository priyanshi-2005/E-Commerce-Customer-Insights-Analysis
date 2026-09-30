-- Top 20% high-value cohort = monetary quintile 5.
-- Techniques: JOINs, CTEs, NTILE, SUM() OVER.

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

, cohort AS (
    SELECT
        CASE WHEN is_top20 = 1 THEN 'Top 20% high-value' ELSE 'Other 80%' END AS cohort,
        COUNT(*) AS customers,
        ROUND(SUM(monetary), 2) AS gmv,
        ROUND(AVG(monetary), 2) AS avg_monetary,
        ROUND(AVG(frequency), 2) AS avg_frequency,
        is_top20
    FROM rfm
    GROUP BY is_top20
)
SELECT
    cohort,
    customers,
    gmv,
    avg_monetary,
    avg_frequency,
    ROUND(gmv * 100.0 / SUM(gmv) OVER (), 2) AS gmv_share_pct
FROM cohort
ORDER BY is_top20 DESC;
