-- Delivery drop-off and review score: top 20% vs everyone else.

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

, ord AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        CASE WHEN o.order_delivered_customer_date IS NULL THEN 1 ELSE 0 END AS dropped
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE strftime('%Y-%m', o.order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
),
rev AS (
    SELECT order_id, AVG(review_score) AS review_score
    FROM order_reviews
    GROUP BY order_id
)
SELECT
    CASE WHEN r.is_top20 = 1 THEN 'Top 20% high-value' ELSE 'Other 80%' END AS cohort,
    COUNT(*) AS orders,
    ROUND(AVG(ord.dropped) * 100, 2) AS dropoff_pct,
    ROUND(AVG(rev.review_score), 2) AS avg_review_score
FROM ord
JOIN rfm r ON ord.customer_unique_id = r.customer_unique_id
LEFT JOIN rev ON ord.order_id = rev.order_id
GROUP BY r.is_top20
ORDER BY r.is_top20 DESC;
