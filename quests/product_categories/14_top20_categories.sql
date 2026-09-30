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

, spend AS (
    SELECT ie.category, SUM(ie.item_gmv) AS revenue
    FROM v_item_enriched ie
    JOIN rfm ON ie.customer_unique_id = rfm.customer_unique_id
    WHERE rfm.is_top20 = 1
      AND ie.purchase_month BETWEEN '2017-01' AND '2018-08'
    GROUP BY ie.category
)
SELECT
    category,
    ROUND(revenue, 2) AS revenue,
    ROUND(revenue * 100.0 / SUM(revenue) OVER (), 2) AS revenue_share_pct
FROM spend
ORDER BY revenue DESC
LIMIT 12;
