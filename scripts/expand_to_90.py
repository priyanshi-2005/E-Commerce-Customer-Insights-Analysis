#!/usr/bin/env python3
"""Add 30 questions (90 total) that back revenue growth, delivery drop-off, RFM, and retention."""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTS = ROOT / "quests"
CATALOG = ROOT / "app" / "quest_catalog.py"
VIEWS = ROOT / "views" / "kpi_views.sql"
DB = ROOT / "data" / "queryquest.db"

RFM = """
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
"""

FLAGS = """
WITH flags AS (
    SELECT
        o.order_id,
        c.customer_unique_id,
        c.customer_state,
        strftime('%Y-%m', o.order_purchase_timestamp) AS purchase_month,
        COALESCE(g.order_gmv, 0) AS order_gmv,
        CASE WHEN o.order_delivered_customer_date IS NOT NULL THEN 1 ELSE 0 END AS is_delivered,
        CASE
            WHEN o.order_delivered_carrier_date IS NOT NULL
              OR o.order_delivered_customer_date IS NOT NULL THEN 1
            ELSE 0
        END AS is_shipped,
        CASE
            WHEN o.order_approved_at IS NOT NULL
              OR o.order_delivered_carrier_date IS NOT NULL
              OR o.order_delivered_customer_date IS NOT NULL THEN 1
            ELSE 0
        END AS is_approved
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN v_order_revenue g ON o.order_id = g.order_id
    WHERE strftime('%Y-%m', o.order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
)
"""

SQL_FILES: dict[str, str] = {
    "revenue_growth/11_mom_delivered_gmv.sql": """
-- Delivered GMV growth. Window: LAG.
WITH monthly AS (
    SELECT
        purchase_month,
        ROUND(SUM(CASE WHEN order_status = 'delivered' THEN order_gmv ELSE 0 END), 2) AS delivered_gmv
    FROM v_order_revenue
    WHERE purchase_month BETWEEN '2017-01' AND '2018-08'
    GROUP BY purchase_month
)
SELECT
    purchase_month,
    delivered_gmv,
    ROUND(
        (delivered_gmv - LAG(delivered_gmv) OVER (ORDER BY purchase_month)) * 100.0
        / NULLIF(LAG(delivered_gmv) OVER (ORDER BY purchase_month), 0),
        2
    ) AS mom_growth_pct
FROM monthly
ORDER BY purchase_month;
""",
    "revenue_growth/12_delivery_conversion.sql": """
-- Purchase-to-delivered conversion by month.
WITH monthly AS (
    SELECT
        strftime('%Y-%m', order_purchase_timestamp) AS purchase_month,
        COUNT(*) AS orders,
        SUM(CASE WHEN order_delivered_customer_date IS NOT NULL THEN 1 ELSE 0 END) AS delivered_orders
    FROM orders
    WHERE strftime('%Y-%m', order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
    GROUP BY purchase_month
)
SELECT
    purchase_month,
    orders,
    delivered_orders,
    ROUND(delivered_orders * 100.0 / orders, 2) AS conversion_pct
FROM monthly
ORDER BY purchase_month;
""",
    "revenue_growth/13_gmv_dropoff.sql": FLAGS
    + """
SELECT
    CASE
        WHEN is_approved = 0 THEN '1. Never approved'
        WHEN is_shipped = 0 THEN '2. Approved, not shipped'
        WHEN is_delivered = 0 THEN '3. Shipped, not delivered'
        ELSE '4. Delivered'
    END AS dropoff_stage,
    COUNT(*) AS orders_lost,
    ROUND(SUM(order_gmv), 2) AS gmv_lost
FROM flags
WHERE is_delivered = 0
GROUP BY dropoff_stage
ORDER BY dropoff_stage;
""",
    "revenue_growth/14_new_vs_repeat_gmv.sql": """
-- New vs repeat GMV. Grain: customer_unique_id. Join + CTE.
WITH firsts AS (
    SELECT customer_unique_id, MIN(purchase_month) AS first_month
    FROM v_order_revenue
    GROUP BY customer_unique_id
)
SELECT
    v.purchase_month,
    ROUND(SUM(CASE WHEN v.purchase_month = f.first_month THEN v.order_gmv ELSE 0 END), 2) AS new_gmv,
    ROUND(SUM(CASE WHEN v.purchase_month > f.first_month THEN v.order_gmv ELSE 0 END), 2) AS repeat_gmv,
    ROUND(
        SUM(CASE WHEN v.purchase_month > f.first_month THEN v.order_gmv ELSE 0 END) * 100.0
        / SUM(v.order_gmv),
        2
    ) AS repeat_share_pct
FROM v_order_revenue v
JOIN firsts f ON v.customer_unique_id = f.customer_unique_id
WHERE v.purchase_month BETWEEN '2017-01' AND '2018-08'
GROUP BY v.purchase_month
ORDER BY v.purchase_month;
""",
    "revenue_growth/15_repeat_gmv_growth.sql": """
-- Month-over-month growth of repeat-customer revenue. Window: LAG.
WITH firsts AS (
    SELECT customer_unique_id, MIN(purchase_month) AS first_month
    FROM v_order_revenue
    GROUP BY customer_unique_id
),
monthly AS (
    SELECT
        v.purchase_month,
        ROUND(SUM(CASE WHEN v.purchase_month > f.first_month THEN v.order_gmv ELSE 0 END), 2) AS repeat_gmv
    FROM v_order_revenue v
    JOIN firsts f ON v.customer_unique_id = f.customer_unique_id
    WHERE v.purchase_month BETWEEN '2017-01' AND '2018-08'
    GROUP BY v.purchase_month
)
SELECT
    purchase_month,
    repeat_gmv,
    ROUND(
        (repeat_gmv - LAG(repeat_gmv) OVER (ORDER BY purchase_month)) * 100.0
        / NULLIF(LAG(repeat_gmv) OVER (ORDER BY purchase_month), 0),
        2
    ) AS mom_growth_pct
FROM monthly
ORDER BY purchase_month;
""",
    "product_categories/11_category_dropoff.sql": """
-- Categories with the worst purchase-to-delivery drop-off.
SELECT
    category,
    COUNT(DISTINCT order_id) AS orders,
    ROUND(
        (COUNT(DISTINCT order_id) - COUNT(DISTINCT CASE WHEN is_delivered = 1 THEN order_id END))
        * 100.0 / COUNT(DISTINCT order_id),
        2
    ) AS dropoff_pct
FROM v_item_enriched
WHERE purchase_month BETWEEN '2017-01' AND '2018-08'
GROUP BY category
HAVING COUNT(DISTINCT order_id) >= 200
ORDER BY dropoff_pct DESC
LIMIT 12;
""",
    "product_categories/12_category_repeat.sql": """
-- Repeat purchase rate by category. Grain: customer_unique_id.
WITH cust_cat AS (
    SELECT category, customer_unique_id, COUNT(DISTINCT order_id) AS orders
    FROM v_item_enriched
    WHERE purchase_month BETWEEN '2017-01' AND '2018-08'
    GROUP BY category, customer_unique_id
)
SELECT
    category,
    COUNT(*) AS customers,
    SUM(CASE WHEN orders > 1 THEN 1 ELSE 0 END) AS repeat_customers,
    ROUND(SUM(CASE WHEN orders > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS repeat_rate_pct
FROM cust_cat
GROUP BY category
HAVING COUNT(*) >= 400
ORDER BY repeat_rate_pct DESC
LIMIT 12;
""",
    "product_categories/13_category_quarter_growth.sql": """
-- Latest quarter vs prior quarter category growth.
WITH cat AS (
    SELECT
        category,
        SUM(CASE WHEN purchase_month BETWEEN '2018-03' AND '2018-05' THEN item_gmv ELSE 0 END) AS prior_gmv,
        SUM(CASE WHEN purchase_month BETWEEN '2018-06' AND '2018-08' THEN item_gmv ELSE 0 END) AS recent_gmv
    FROM v_item_enriched
    GROUP BY category
)
SELECT
    category,
    ROUND(prior_gmv, 2) AS prior_gmv,
    ROUND(recent_gmv, 2) AS recent_gmv,
    ROUND((recent_gmv - prior_gmv) * 100.0 / NULLIF(prior_gmv, 0), 2) AS growth_pct
FROM cat
WHERE prior_gmv >= 8000
ORDER BY growth_pct DESC
LIMIT 12;
""",
    "product_categories/14_top20_categories.sql": RFM
    + """
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
""",
    "product_categories/15_category_delivery_conversion.sql": """
-- Order value that actually gets delivered, by category.
WITH cat AS (
    SELECT
        category,
        SUM(item_gmv) AS ordered_gmv,
        SUM(CASE WHEN is_delivered = 1 THEN item_gmv ELSE 0 END) AS delivered_gmv
    FROM v_item_enriched
    WHERE purchase_month BETWEEN '2017-01' AND '2018-08'
    GROUP BY category
)
SELECT
    category,
    ROUND(ordered_gmv, 2) AS ordered_gmv,
    ROUND(delivered_gmv, 2) AS delivered_gmv,
    ROUND(delivered_gmv * 100.0 / NULLIF(ordered_gmv, 0), 2) AS delivery_conversion_pct
FROM cat
WHERE ordered_gmv >= 20000
ORDER BY delivery_conversion_pct ASC
LIMIT 12;
""",
    "customer_analytics/11_rfm_distribution.sql": """
-- RFM score distribution.
-- Techniques: JOINs, CTEs, window functions (NTILE on recency, frequency, monetary).
"""
    + RFM
    + """
SELECT
    rfm_score,
    COUNT(*) AS customers,
    ROUND(AVG(monetary), 2) AS avg_monetary,
    ROUND(SUM(monetary), 2) AS gmv
FROM rfm
GROUP BY rfm_score
ORDER BY rfm_score;
""",
    "customer_analytics/12_top20_cohort.sql": """
-- Top 20% high-value cohort = monetary quintile 5.
-- Techniques: JOINs, CTEs, NTILE, SUM() OVER.
"""
    + RFM
    + """
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
""",
    "customer_analytics/13_rfm_segments.sql": """
-- RFM segments for retention targeting.
-- Techniques: JOINs, CTEs, NTILE window scores.
"""
    + RFM
    + """
SELECT
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN m_score >= 4 AND r_score <= 2 THEN 'At Risk'
        WHEN f_score >= 4 AND m_score >= 3 THEN 'Loyal'
        WHEN m_score = 5 AND f_score <= 2 THEN 'Big Spenders'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Hibernating'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'Recent'
        ELSE 'Need Attention'
    END AS segment,
    COUNT(*) AS customers,
    ROUND(SUM(monetary), 2) AS gmv,
    ROUND(AVG(recency_days), 1) AS avg_recency_days
FROM rfm
GROUP BY segment
ORDER BY gmv DESC;
""",
    "customer_analytics/14_mom_retention.sql": """
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
""",
    "customer_analytics/15_lapsing_high_value.sql": """
-- High-value customers (top 20%) split by how recently they ordered.
-- Retention target: 91+ day buckets.
"""
    + RFM
    + """
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
""",
    "payments_checkout/11_approval_by_type.sql": """
-- Checkout approval conversion by payment type. Join.
SELECT
    op.payment_type,
    COUNT(DISTINCT o.order_id) AS orders,
    COUNT(DISTINCT CASE WHEN o.order_approved_at IS NOT NULL THEN o.order_id END) AS approved_orders,
    ROUND(
        COUNT(DISTINCT CASE WHEN o.order_approved_at IS NOT NULL THEN o.order_id END) * 100.0
        / COUNT(DISTINCT o.order_id),
        2
    ) AS approval_rate_pct
FROM orders o
JOIN order_payments op ON o.order_id = op.order_id
WHERE strftime('%Y-%m', o.order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
GROUP BY op.payment_type
ORDER BY orders DESC;
""",
    "payments_checkout/12_mom_checkout_conversion.sql": """
-- Month-over-month purchase-to-approval conversion.
WITH monthly AS (
    SELECT
        strftime('%Y-%m', order_purchase_timestamp) AS purchase_month,
        COUNT(*) AS orders,
        SUM(CASE WHEN order_approved_at IS NOT NULL THEN 1 ELSE 0 END) AS approved_orders
    FROM orders
    WHERE strftime('%Y-%m', order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
    GROUP BY purchase_month
)
SELECT
    purchase_month,
    orders,
    approved_orders,
    ROUND(approved_orders * 100.0 / orders, 2) AS conversion_pct,
    ROUND(
        approved_orders * 100.0 / orders
        - LAG(approved_orders * 100.0 / orders) OVER (ORDER BY purchase_month),
        2
    ) AS conversion_change_pct
FROM monthly
ORDER BY purchase_month;
""",
    "payments_checkout/13_payment_dropoff_gmv.sql": FLAGS
    + """
SELECT
    purchase_month,
    SUM(CASE WHEN is_approved = 0 THEN 1 ELSE 0 END) AS unapproved_orders,
    ROUND(SUM(CASE WHEN is_approved = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS dropoff_pct,
    ROUND(SUM(CASE WHEN is_approved = 0 THEN order_gmv ELSE 0 END), 2) AS gmv_at_risk
FROM flags
GROUP BY purchase_month
ORDER BY purchase_month;
""",
    "payments_checkout/14_top20_conversion.sql": """
-- Do the top 20% monetary cohort convert better?
"""
    + RFM
    + """
, order_cust AS (
    SELECT
        c.customer_unique_id,
        CASE WHEN o.order_approved_at IS NOT NULL THEN 1 ELSE 0 END AS is_approved,
        CASE WHEN o.order_delivered_customer_date IS NOT NULL THEN 1 ELSE 0 END AS is_delivered
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE strftime('%Y-%m', o.order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
)
SELECT
    CASE WHEN r.is_top20 = 1 THEN 'Top 20% high-value' ELSE 'Other 80%' END AS cohort,
    COUNT(*) AS orders,
    ROUND(AVG(oc.is_approved) * 100, 2) AS approval_rate_pct,
    ROUND(AVG(oc.is_delivered) * 100, 2) AS delivery_rate_pct
FROM order_cust oc
JOIN rfm r ON oc.customer_unique_id = r.customer_unique_id
GROUP BY r.is_top20
ORDER BY r.is_top20 DESC;
""",
    "payments_checkout/15_repeat_by_first_payment.sql": """
-- Which first payment type is followed by a second order?
-- Window: ROW_NUMBER. Grain: customer_unique_id.
WITH first_order AS (
    SELECT
        customer_unique_id,
        order_id,
        ROW_NUMBER() OVER (
            PARTITION BY customer_unique_id
            ORDER BY order_purchase_timestamp
        ) AS rn
    FROM v_order_revenue
),
first_pay AS (
    SELECT
        f.customer_unique_id,
        op.payment_type,
        CASE WHEN c.total_orders > 1 THEN 1 ELSE 0 END AS did_repeat
    FROM first_order f
    JOIN order_payments op ON f.order_id = op.order_id AND op.payment_sequential = 1
    JOIN v_customer_orders c ON f.customer_unique_id = c.customer_unique_id
    WHERE f.rn = 1
)
SELECT
    payment_type,
    COUNT(*) AS customers,
    SUM(did_repeat) AS repeat_customers,
    ROUND(AVG(did_repeat) * 100, 2) AS repeat_rate_pct
FROM first_pay
GROUP BY payment_type
HAVING COUNT(*) >= 50
ORDER BY customers DESC;
""",
    "logistics_reviews/11_delivery_funnel.sql": """
-- Delivery drop-off funnel. Windows: LAG, FIRST_VALUE.
"""
    + FLAGS
    + """
, stages AS (
    SELECT 1 AS stage_order, 'Purchased' AS stage, COUNT(*) AS orders FROM flags
    UNION ALL
    SELECT 2, 'Approved', COUNT(*) FROM flags WHERE is_approved = 1
    UNION ALL
    SELECT 3, 'Shipped', COUNT(*) FROM flags WHERE is_shipped = 1
    UNION ALL
    SELECT 4, 'Delivered', COUNT(*) FROM flags WHERE is_delivered = 1
),
with_lag AS (
    SELECT
        stage_order,
        stage,
        orders,
        ROUND(orders * 100.0 / FIRST_VALUE(orders) OVER (ORDER BY stage_order), 2) AS conversion_from_start_pct,
        LAG(orders) OVER (ORDER BY stage_order) AS prior_orders
    FROM stages
)
SELECT
    stage,
    orders,
    conversion_from_start_pct,
    ROUND(
        CASE
            WHEN prior_orders IS NULL THEN 0
            ELSE (prior_orders - orders) * 100.0 / prior_orders
        END,
        2
    ) AS dropoff_from_prior_pct
FROM with_lag
ORDER BY stage_order;
""",
    "logistics_reviews/12_dropoff_by_month.sql": FLAGS
    + """
SELECT
    purchase_month,
    COUNT(*) AS orders,
    SUM(CASE WHEN is_delivered = 0 THEN 1 ELSE 0 END) AS dropped_orders,
    ROUND(SUM(CASE WHEN is_delivered = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS dropoff_pct
FROM flags
GROUP BY purchase_month
ORDER BY purchase_month;
""",
    "logistics_reviews/13_dropoff_by_state.sql": FLAGS
    + """
SELECT
    customer_state,
    COUNT(*) AS orders,
    ROUND(SUM(CASE WHEN is_delivered = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS dropoff_pct,
    ROUND(SUM(CASE WHEN is_delivered = 0 THEN order_gmv ELSE 0 END), 2) AS gmv_lost
FROM flags
GROUP BY customer_state
HAVING COUNT(*) >= 300
ORDER BY dropoff_pct DESC
LIMIT 12;
""",
    "logistics_reviews/14_mom_delivery_quality.sql": """
-- Delivery conversion and on-time rate by month.
WITH monthly AS (
    SELECT
        strftime('%Y-%m', order_purchase_timestamp) AS purchase_month,
        AVG(CASE WHEN order_delivered_customer_date IS NOT NULL THEN 1.0 ELSE 0 END) AS delivery_conversion,
        AVG(
            CASE
                WHEN order_delivered_customer_date IS NULL THEN NULL
                WHEN julianday(order_delivered_customer_date) - julianday(order_estimated_delivery_date) <= 0 THEN 1.0
                ELSE 0
            END
        ) AS on_time
    FROM orders
    WHERE strftime('%Y-%m', order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
    GROUP BY purchase_month
)
SELECT
    purchase_month,
    ROUND(delivery_conversion * 100, 2) AS delivery_conversion_pct,
    ROUND(on_time * 100, 2) AS on_time_pct
FROM monthly
ORDER BY purchase_month;
""",
    "logistics_reviews/15_top20_dropoff.sql": """
-- Delivery drop-off and review score: top 20% vs everyone else.
"""
    + RFM
    + """
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
""",
    "sellers_marketplace/11_seller_dropoff.sql": """
-- Sellers with the most GMV stuck before delivery.
WITH seller_orders AS (
    SELECT
        oi.seller_id,
        s.seller_city,
        oi.order_id,
        MAX(CASE WHEN o.order_delivered_customer_date IS NULL THEN 1 ELSE 0 END) AS dropped,
        SUM(oi.price + oi.freight_value) AS gmv
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN sellers s ON oi.seller_id = s.seller_id
    WHERE strftime('%Y-%m', o.order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
    GROUP BY oi.seller_id, s.seller_city, oi.order_id
)
SELECT
    seller_city || ' · ' || substr(seller_id, 1, 8) AS seller_label,
    COUNT(*) AS orders,
    ROUND(AVG(dropped) * 100, 2) AS dropoff_pct,
    ROUND(SUM(CASE WHEN dropped = 1 THEN gmv ELSE 0 END), 2) AS gmv_lost
FROM seller_orders
GROUP BY seller_id, seller_city
HAVING COUNT(*) >= 80
ORDER BY gmv_lost DESC
LIMIT 12;
""",
    "sellers_marketplace/12_seller_mom_retention.sql": """
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
""",
    "sellers_marketplace/13_top20_sellers.sql": """
-- Sellers who serve the top 20% high-value cohort.
"""
    + RFM
    + """
SELECT
    s.seller_city || ' · ' || substr(ie.seller_id, 1, 8) AS seller_label,
    COUNT(DISTINCT ie.order_id) AS orders,
    ROUND(SUM(ie.item_gmv), 2) AS revenue
FROM v_item_enriched ie
JOIN rfm
  ON ie.customer_unique_id = rfm.customer_unique_id
 AND rfm.is_top20 = 1
JOIN sellers s ON ie.seller_id = s.seller_id
WHERE ie.purchase_month BETWEEN '2017-01' AND '2018-08'
GROUP BY ie.seller_id, s.seller_city
ORDER BY revenue DESC
LIMIT 12;
""",
    "sellers_marketplace/14_state_ship_conversion.sql": """
-- Shipped-to-delivered conversion by seller state.
WITH seller_orders AS (
    SELECT
        s.seller_state,
        oi.order_id,
        MAX(CASE
            WHEN o.order_delivered_carrier_date IS NOT NULL
              OR o.order_delivered_customer_date IS NOT NULL THEN 1
            ELSE 0
        END) AS shipped,
        MAX(CASE WHEN o.order_delivered_customer_date IS NOT NULL THEN 1 ELSE 0 END) AS delivered
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN sellers s ON oi.seller_id = s.seller_id
    WHERE strftime('%Y-%m', o.order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
    GROUP BY s.seller_state, oi.order_id
)
SELECT
    seller_state,
    SUM(shipped) AS shipped_orders,
    SUM(delivered) AS delivered_orders,
    ROUND(SUM(delivered) * 100.0 / NULLIF(SUM(shipped), 0), 2) AS conversion_pct
FROM seller_orders
GROUP BY seller_state
HAVING SUM(shipped) >= 200
ORDER BY conversion_pct ASC;
""",
    "sellers_marketplace/15_seller_repeat_rate.sql": """
-- Which sellers bring the same customer back? Grain: customer_unique_id.
WITH seller_cust AS (
    SELECT
        oi.seller_id,
        s.seller_city,
        c.customer_unique_id,
        COUNT(DISTINCT oi.order_id) AS orders
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN sellers s ON oi.seller_id = s.seller_id
    WHERE strftime('%Y-%m', o.order_purchase_timestamp) BETWEEN '2017-01' AND '2018-08'
    GROUP BY oi.seller_id, s.seller_city, c.customer_unique_id
)
SELECT
    seller_city || ' · ' || substr(seller_id, 1, 8) AS seller_label,
    COUNT(*) AS customers,
    ROUND(SUM(CASE WHEN orders > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS repeat_rate_pct
FROM seller_cust
GROUP BY seller_id, seller_city
HAVING COUNT(*) >= 100
ORDER BY repeat_rate_pct DESC
LIMIT 12;
""",
}

INSERTS = {
    'analyst="Correlation computed across monthly aggregates."),': """
            _q("rg11", "How fast is delivered GMV growing month over month?", "revenue_growth/11_mom_delivered_gmv.sql",
               metrics=[("Latest MoM Growth", "mom_growth_pct", "last", "pct"), ("Peak Delivered GMV", "delivered_gmv", "max", "currency"), ("Avg MoM Growth", "mom_growth_pct", "mean", "pct")],
               chart=("line", "purchase_month", "mom_growth_pct", "Delivered GMV Growth %"),
               product="Scale campaigns in months where delivered GMV accelerates.", finance="Forecast recognized revenue off delivered GMV, not gross orders.", analyst="LAG window on monthly delivered GMV; first month growth is null."),
            _q("rg12", "What share of purchases actually get delivered each month?", "revenue_growth/12_delivery_conversion.sql",
               metrics=[("Latest Conversion", "conversion_pct", "last", "pct"), ("Avg Conversion", "conversion_pct", "mean", "pct"), ("Total Orders", "orders", "sum", "int")],
               chart=("line", "purchase_month", "conversion_pct", "Purchase-to-Delivery Conversion"),
               product="A falling conversion rate is a delivery promise problem, not a traffic problem.", finance="Undelivered orders should not be treated as earned revenue.", analyst="Conversion = delivered timestamp / orders that month."),
            _q("rg13", "Where is GMV lost in the delivery drop-off funnel?", "revenue_growth/13_gmv_dropoff.sql",
               metrics=[("GMV Lost", "gmv_lost", "sum", "currency"), ("Orders Lost", "orders_lost", "sum", "int"), ("Biggest Leak", "gmv_lost", "max", "currency")],
               chart=("bar", "dropoff_stage", "gmv_lost", "GMV Lost by Drop-off Stage"),
               product="Fix the stage with the largest GMV leak first.", finance="This is revenue sitting before delivery.", analyst="Stages are mutually exclusive: never approved, not shipped, not delivered."),
            _q("rg14", "How much monthly GMV comes from repeat vs new customers?", "revenue_growth/14_new_vs_repeat_gmv.sql",
               metrics=[("Latest Repeat Share", "repeat_share_pct", "last", "pct"), ("Repeat GMV", "repeat_gmv", "sum", "currency"), ("New GMV", "new_gmv", "sum", "currency")],
               chart=("line", "purchase_month", "repeat_share_pct", "Repeat GMV Share"),
               product="If repeat share stays tiny, acquisition is carrying the business.", finance="Repeat GMV is cheaper revenue than first-order GMV.", analyst="Repeat uses customer_unique_id, not the per-order customer_id."),
            _q("rg15", "Is repeat-customer revenue growing month over month?", "revenue_growth/15_repeat_gmv_growth.sql",
               metrics=[("Latest Repeat Growth", "mom_growth_pct", "last", "pct"), ("Total Repeat GMV", "repeat_gmv", "sum", "currency"), ("Best Growth Month", "mom_growth_pct", "max", "pct")],
               chart=("line", "purchase_month", "mom_growth_pct", "Repeat GMV MoM Growth"),
               product="Put retention budget where repeat GMV growth stalls.", finance="Repeat GMV growth is the retention P&L.", analyst="Early months can be null or spiky because the repeat base is small."),
""",
    'analyst="Median reduces outlier skew vs mean."),': """
            _q("pc11", "Which categories lose the most orders before delivery?", "product_categories/11_category_dropoff.sql",
               metrics=[("Worst Drop-off", "dropoff_pct", "max", "pct"), ("Categories Shown", "category", "count", "int")],
               chart=("bar", "category", "dropoff_pct", "Category Delivery Drop-off"),
               product="Pause ads on categories that fail delivery.", finance="Drop-off here is lost category revenue.", analyst="Limited to categories with at least 200 orders."),
            _q("pc12", "Which categories have the highest repeat-purchase rate?", "product_categories/12_category_repeat.sql",
               metrics=[("Best Repeat Rate", "repeat_rate_pct", "max", "pct"), ("Avg Repeat Rate", "repeat_rate_pct", "mean", "pct")],
               chart=("bar", "category", "repeat_rate_pct", "Repeat Rate by Category"),
               product="Build replenishment nudges for high-repeat categories.", finance="Repeat categories support a higher CAC.", analyst="A repeat is 2+ orders in the same category by the same person."),
            _q("pc13", "Which categories grew fastest in the latest quarter?", "product_categories/13_category_quarter_growth.sql",
               metrics=[("Fastest Growth", "growth_pct", "max", "pct"), ("Categories Shown", "category", "count", "int")],
               chart=("bar", "category", "growth_pct", "Quarterly Category Growth"),
               product="Feature the fastest-growing categories next quarter.", finance="Use this mix shift in the next revenue forecast.", analyst="Compares Jun-Aug 2018 with Mar-May 2018, prior GMV at least R$8k."),
            _q("pc14", "What do the top 20% high-value customers buy?", "product_categories/14_top20_categories.sql",
               metrics=[("Top Category Revenue", "revenue", "max", "currency"), ("Listed Category Revenue", "revenue", "sum", "currency")],
               chart=("bar", "category", "revenue", "Top 20% Cohort — Categories"),
               product="Merchandize the homepage for this cohort, not the average buyer.", finance="This basket is where high-value GMV concentrates.", analyst="Top 20% = monetary NTILE score 5, joined back to items."),
            _q("pc15", "Which categories convert from order to delivery the worst?", "product_categories/15_category_delivery_conversion.sql",
               metrics=[("Lowest Conversion", "delivery_conversion_pct", "min", "pct"), ("Delivered GMV", "delivered_gmv", "sum", "currency")],
               chart=("bar", "category", "delivery_conversion_pct", "Delivery Conversion by Category"),
               product="Treat low conversion as an ops issue before adding more SKUs.", finance="Ordered GMV overstates what the category actually delivers.", analyst="Sorted ascending so the worst converters are first."),
""",
    'analyst="Churn proxy = no order in 180 days."),': """
            _q("ca11", "How are customers distributed across RFM scores?", "customer_analytics/11_rfm_distribution.sql",
               metrics=[("Customers Scored", "customers", "sum", "int"), ("Highest Score Band", "rfm_score", "max", "int"), ("Top Band GMV", "gmv", "max", "currency")],
               chart=("bar", "rfm_score", "customers", "Customers by RFM Score"),
               product="Use the score, not a single average, to pick who gets which message.", finance="Higher scores concentrate a disproportionate share of GMV.", analyst="R, F, and M are NTILE(5) window scores. RFM score = R + F + M (3 to 15)."),
            _q("ca12", "How much GMV does the top 20% high-value cohort contribute?", "customer_analytics/12_top20_cohort.sql",
               metrics=[("Top 20% GMV Share", "gmv_share_pct", "first", "pct"), ("Top 20% Customers", "customers", "first", "int"), ("Top 20% GMV", "gmv", "first", "currency")],
               chart=("bar", "cohort", "gmv", "GMV: Top 20% vs Other 80%"),
               product="Build a separate retention track for this cohort.", finance="This is the revenue at risk if high-value customers go quiet.", analyst="Top 20% is monetary quintile 5 from NTILE, not a hand-picked list."),
            _q("ca13", "Which RFM segments should retention campaigns target?", "customer_analytics/13_rfm_segments.sql",
               metrics=[("Largest Segment", "customers", "max", "int"), ("Segment GMV", "gmv", "sum", "currency"), ("Segments", "segment", "count", "int")],
               chart=("bar", "segment", "gmv", "GMV by RFM Segment"),
               product="Message At Risk and Hibernating differently from Champions.", finance="At Risk is high monetary value with stale recency — protect it first.", analyst="Segment rules sit on top of the 1-5 R/F/M scores."),
            _q("ca14", "What is month-over-month customer retention?", "customer_analytics/14_mom_retention.sql",
               metrics=[("Latest Retention", "mom_retention_pct", "last", "pct"), ("Best Retention", "mom_retention_pct", "max", "pct"), ("Avg Retention", "mom_retention_pct", "mean", "pct")],
               chart=("line", "month", "mom_retention_pct", "Month-over-Month Retention"),
               product="A retention dip is the trigger for a win-back campaign that month.", finance="MoM retention is the leading indicator for next month's repeat GMV.", analyst="Retained = ordered this month and last month, using customer_unique_id."),
            _q("ca15", "How much high-value GMV is going quiet?", "customer_analytics/15_lapsing_high_value.sql",
               metrics=[("High-Value Customers", "customers", "sum", "int"), ("Lapsed High-Value GMV", "gmv", "last", "currency"), ("Watchlist Customers", "customers", "max", "int")],
               chart=("bar", "recency_bucket", "customers", "Top 20% by Recency"),
               product="Start with the 91-180 day bucket before they hit 180+.", finance="Lapsed GMV is the retention opportunity, not new-user CAC.", analyst="Restricted to monetary quintile 5. Recency is days since last order."),
""",
    'analyst="Grouped by month and payment type."),': """
            _q("pay11", "Which payment types have the weakest approval conversion?", "payments_checkout/11_approval_by_type.sql",
               metrics=[("Best Approval", "approval_rate_pct", "max", "pct"), ("Weakest Approval", "approval_rate_pct", "min", "pct"), ("Payment Types", "payment_type", "count", "int")],
               chart=("bar", "payment_type", "approval_rate_pct", "Approval Conversion by Payment"),
               product="Simplify the payment type with the weakest approval rate.", finance="Failed approval is checkout revenue that never starts.", analyst="Approval = order_approved_at is present."),
            _q("pay12", "How does checkout conversion change month over month?", "payments_checkout/12_mom_checkout_conversion.sql",
               metrics=[("Latest Conversion", "conversion_pct", "last", "pct"), ("Avg Conversion", "conversion_pct", "mean", "pct"), ("Worst Change", "conversion_change_pct", "min", "pct")],
               chart=("line", "purchase_month", "conversion_pct", "Checkout Conversion Trend"),
               product="Investigate months where conversion drops, not just the average.", finance="Conversion change is a revenue variance driver.", analyst="LAG compares each month with the previous month."),
            _q("pay13", "How much GMV is stuck before payment approval each month?", "payments_checkout/13_payment_dropoff_gmv.sql",
               metrics=[("Peak Drop-off", "dropoff_pct", "max", "pct"), ("GMV at Risk", "gmv_at_risk", "sum", "currency"), ("Unapproved Orders", "unapproved_orders", "sum", "int")],
               chart=("line", "purchase_month", "dropoff_pct", "Payment Drop-off Rate"),
               product="Add a retry or reminder on the unapproved path.", finance="GMV at risk is not yet collectible.", analyst="Drop-off = orders with no approval and no later shipment."),
            _q("pay14", "Do top 20% customers convert better at checkout and delivery?", "payments_checkout/14_top20_conversion.sql",
               metrics=[("Top 20% Approval", "approval_rate_pct", "first", "pct"), ("Top 20% Delivery", "delivery_rate_pct", "first", "pct"), ("Top 20% Orders", "orders", "first", "int")],
               chart=("bar", "cohort", "approval_rate_pct", "Approval Rate by Cohort"),
               product="If the best customers convert worse, the friction is in the premium path.", finance="Compare cohort conversion before spending more on acquisition.", analyst="Cohort is the same monetary quintile used in the RFM quest."),
            _q("pay15", "Which first payment type leads to a second order?", "payments_checkout/15_repeat_by_first_payment.sql",
               metrics=[("Best Repeat Rate", "repeat_rate_pct", "max", "pct"), ("Customers", "customers", "sum", "int")],
               chart=("bar", "payment_type", "repeat_rate_pct", "Repeat Rate by First Payment"),
               product="Default new users into the payment type that retains.", finance="Payment mix is a retention lever, not only a fee lever.", analyst="First order uses ROW_NUMBER; repeat uses customer_unique_id."),
""",
    'analyst="Monthly avg review_score."),': """
            _q("lr11", "Where do orders drop off between purchase and delivery?", "logistics_reviews/11_delivery_funnel.sql",
               metrics=[("Delivered Conversion", "conversion_from_start_pct", "last", "pct"), ("Purchased Orders", "orders", "first", "int"), ("Biggest Stage Drop", "dropoff_from_prior_pct", "max", "pct")],
               chart=("bar", "stage", "orders", "Delivery Funnel"),
               product="The biggest stage drop is the ops fix, not a blanket 'delivery' problem.", finance="Only the Delivered stage is completed demand.", analyst="Funnel is monotonic. LAG measures drop-off from the prior stage."),
            _q("lr12", "Which months have the worst delivery drop-off?", "logistics_reviews/12_dropoff_by_month.sql",
               metrics=[("Worst Drop-off", "dropoff_pct", "max", "pct"), ("Avg Drop-off", "dropoff_pct", "mean", "pct"), ("Dropped Orders", "dropped_orders", "sum", "int")],
               chart=("line", "purchase_month", "dropoff_pct", "Delivery Drop-off by Month"),
               product="Staff carriers before the months that historically drop off.", finance="Drop-off spikes are a revenue timing risk.", analyst="Drop-off = no customer delivery timestamp."),
            _q("lr13", "Which states have the highest delivery drop-off?", "logistics_reviews/13_dropoff_by_state.sql",
               metrics=[("Worst State Drop-off", "dropoff_pct", "max", "pct"), ("GMV Lost", "gmv_lost", "sum", "currency")],
               chart=("bar", "customer_state", "dropoff_pct", "Drop-off by State"),
               product="Change the carrier or promise in the worst states.", finance="GMV lost is state-level leakage.", analyst="States with under 300 orders are hidden so tiny samples don't rank first."),
            _q("lr14", "Are delivery conversion and on-time rate improving?", "logistics_reviews/14_mom_delivery_quality.sql",
               metrics=[("Latest Delivery Conversion", "delivery_conversion_pct", "last", "pct"), ("Latest On-Time", "on_time_pct", "last", "pct"), ("Best On-Time", "on_time_pct", "max", "pct")],
               chart=("line", "purchase_month", "delivery_conversion_pct", "Delivery Conversion"), chart2=("line", "purchase_month", "on_time_pct", "On-Time Rate"),
               product="Track both completion and lateness — a delivered-but-late order still hurts retention.", finance="On-time failure shows up later as lower repeat GMV.", analyst="On-time = delivered on or before the estimated date."),
            _q("lr15", "Do top 20% customers see fewer delivery drop-offs?", "logistics_reviews/15_top20_dropoff.sql",
               metrics=[("Top 20% Drop-off", "dropoff_pct", "first", "pct"), ("Top 20% Review", "avg_review_score", "first", "float"), ("Top 20% Orders", "orders", "first", "int")],
               chart=("bar", "cohort", "dropoff_pct", "Drop-off by Value Cohort"),
               product="High-value customers should not have a worse delivery experience.", finance="A drop-off gap on this cohort is expensive churn.", analyst="Same RFM top quintile, joined to orders and reviews."),
""",
    'analyst="Top 20 sellers by revenue."),': """
            _q("sm11", "Which sellers create the most delivery drop-off?", "sellers_marketplace/11_seller_dropoff.sql",
               metrics=[("Worst Drop-off", "dropoff_pct", "max", "pct"), ("GMV Lost", "gmv_lost", "sum", "currency"), ("Sellers Shown", "seller_label", "count", "int")],
               chart=("bar", "seller_label", "gmv_lost", "GMV Lost by Seller"),
               product="Coach or throttle sellers who fail to deliver.", finance="Their GMV lost is marketplace leakage.", analyst="Seller must have at least 80 orders. Ranked by GMV lost."),
            _q("sm12", "What is month-over-month seller retention?", "sellers_marketplace/12_seller_mom_retention.sql",
               metrics=[("Latest Seller Retention", "mom_retention_pct", "last", "pct"), ("Avg Retention", "mom_retention_pct", "mean", "pct"), ("Best Retention", "mom_retention_pct", "max", "pct")],
               chart=("line", "month", "mom_retention_pct", "Seller MoM Retention"),
               product="A seller who disappears is a supply problem for next month's conversion.", finance="Seller churn reduces available GMV.", analyst="Retained = sold this month and the previous month."),
            _q("sm13", "Which sellers serve the top 20% high-value cohort?", "sellers_marketplace/13_top20_sellers.sql",
               metrics=[("Top Seller Revenue", "revenue", "max", "currency"), ("Listed Revenue", "revenue", "sum", "currency")],
               chart=("bar", "seller_label", "revenue", "Sellers of the Top 20%"),
               product="Protect the relationship with sellers this cohort already trusts.", finance="This is the supply base behind high-value GMV.", analyst="Joined from the RFM monetary quintile to order items."),
            _q("sm14", "Which seller states convert shipped orders to delivered the worst?", "sellers_marketplace/14_state_ship_conversion.sql",
               metrics=[("Lowest Conversion", "conversion_pct", "min", "pct"), ("States Shown", "seller_state", "count", "int")],
               chart=("bar", "seller_state", "conversion_pct", "Shipped-to-Delivered by Seller State"),
               product="Last-mile fixes should start in the worst seller states.", finance="Shipped but not delivered is cost without revenue.", analyst="Conversion = delivered orders / shipped orders, minimum 200 shipped."),
            _q("sm15", "Which sellers are best at bringing customers back?", "sellers_marketplace/15_seller_repeat_rate.sql",
               metrics=[("Best Repeat Rate", "repeat_rate_pct", "max", "pct"), ("Sellers Shown", "seller_label", "count", "int")],
               chart=("bar", "seller_label", "repeat_rate_pct", "Seller Repeat Rate"),
               product="Study what high-repeat sellers do and copy it into onboarding.", finance="Repeat rate is a seller-quality metric, not just a GMV rank.", analyst="Repeat = the same customer_unique_id orders from that seller twice."),
""",
}

DESCRIPTIONS = {
    '"GMV trends, growth rates, and revenue concentration."': '"GMV growth, purchase-to-delivery conversion, and revenue lost at drop-off."',
    '"Category performance, assortment, and catalog insights."': '"Category revenue, repeat purchase, and delivery conversion."',
    '"Segments, retention, lifetime value, and repeat behavior."': '"RFM scores, the top 20% high-value cohort, and month-over-month retention."',
    '"Payment mix, installments, friction, and completion."': '"Payment mix, checkout conversion, and GMV stuck before approval."',
    '"Delivery performance, fulfillment funnel, and satisfaction."': '"Delivery drop-off funnel, on-time rate, and review impact."',
    '"Seller concentration, geography, and marketplace health."': '"Seller drop-off, month-over-month seller retention, and high-value supply."',
}


def write_sql() -> None:
    for rel, sql in SQL_FILES.items():
        path = QUESTS / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(sql.strip() + "\n", encoding="utf-8")
    print(f"Wrote {len(SQL_FILES)} SQL files")


def fix_customer_grain() -> None:
    """Olist customer_id is per order. Retention must use customer_unique_id."""
    folder = QUESTS / "customer_analytics"
    for name in [
        "01_customer_segments.sql",
        "03_top_customers.sql",
        "05_new_customers.sql",
        "06_repeat_rate_cohort.sql",
        "07_cohort_retention.sql",
        "08_time_to_second_order.sql",
        "09_customers_by_state.sql",
        "10_churn_proxy.sql",
    ]:
        path = folder / name
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("customer_id", "customer_unique_id"), encoding="utf-8")
    print("Repointed customer analytics queries to customer_unique_id")


def patch_catalog() -> None:
    text = CATALOG.read_text(encoding="utf-8")
    if "ca11" in text:
        print("Catalog already has the extra questions")
    else:
        for anchor, block in INSERTS.items():
            if anchor not in text:
                raise SystemExit(f"Catalog anchor missing: {anchor}")
            text = text.replace(anchor, anchor + block, 1)
    for old, new in DESCRIPTIONS.items():
        text = text.replace(old, new)
    text = text.replace(
        "Quest catalog: 6 quests × 10 questions each.",
        "Quest catalog: 6 quests × 15 questions each.",
    )
    CATALOG.write_text(text, encoding="utf-8")
    print("Updated quest catalog")


def patch_app_and_readme() -> None:
    app = ROOT / "app" / "streamlit_app.py"
    app_text = app.read_text(encoding="utf-8")
    app_text = app_text.replace(
        "Each quest has 10 business questions you can explore.",
        "Each quest has 15 business questions you can explore.",
    )
    app_text = app_text.replace(
        'st.caption(f"{category[\'lens\']} · Pick one of 10 questions")',
        'st.caption(f"{category[\'lens\']} · Pick one of {len(category[\'questions\'])} questions")',
    )
    app.write_text(app_text, encoding="utf-8")

    readme = ROOT / "README.md"
    readme_text = readme.read_text(encoding="utf-8")
    readme_text = readme_text.replace("6 Quests** × **10 questions** each (60 total)", "6 Quests** × **15 questions** each (90 total)")
    readme_text = readme_text.replace("6 quests × 10 questions metadata", "6 quests × 15 questions metadata")
    readme_text = readme_text.replace("6 folders, 10 SQL files each", "6 folders, 15 SQL files each")
    readme_text = readme_text.replace("## Quests (6 × 10)", "## Quests (6 × 15)")
    readme_text = readme_text.replace(
        "| Revenue & Growth | GMV, MoM growth, AOV, concentration |\n"
        "| Product & Categories | Category revenue, AOV, catalog insights |\n"
        "| Customer Analytics | Segments, retention, LTV, churn proxy |\n"
        "| Payments & Checkout | Payment mix, installments, friction |\n"
        "| Logistics & Reviews | Delivery delay, review scores, funnel |\n"
        "| Sellers & Marketplace | Seller leaderboard, concentration |",
        "| Revenue & Growth | Delivered GMV growth, conversion, drop-off leakage |\n"
        "| Product & Categories | Category repeat, growth, delivery conversion |\n"
        "| Customer Analytics | RFM scores, top 20% cohort, MoM retention |\n"
        "| Payments & Checkout | Approval conversion, payment drop-off |\n"
        "| Logistics & Reviews | Delivery funnel drop-off, on-time rate |\n"
        "| Sellers & Marketplace | Seller drop-off, seller retention, high-value supply |",
    )
    readme_text = readme_text.replace(
        "Each quest has **10 questions** → dashboard (KPIs, charts, table, recommendations) + **SQL below**.",
        "Each quest has **15 questions** → dashboard (KPIs, charts, table, recommendations) + **SQL below**.\n\n"
        "Customer metrics use `customer_unique_id`. Olist creates a new `customer_id` on every order, so RFM and retention would be wrong on `customer_id`.\n\n"
        "Questions that defend the main story:\n\n"
        "- Revenue growth and delivery conversion: Revenue quest, questions 11–15\n"
        "- Delivery drop-off funnel: Logistics quest, questions 11–15\n"
        "- RFM scores and the top 20% cohort: Customer quest, questions 11–13 and 15\n"
        "- Month-over-month retention: Customer question 14, Seller question 12\n"
        "- Checkout conversion: Payments quest, questions 11–15",
    )
    readme.write_text(readme_text, encoding="utf-8")
    print("Updated app copy and README")


def apply_views() -> None:
    with sqlite3.connect(DB) as conn:
        conn.executescript(VIEWS.read_text(encoding="utf-8"))
    print("Rebuilt KPI views")


def main() -> None:
    write_sql()
    fix_customer_grain()
    patch_catalog()
    patch_app_and_readme()
    apply_views()


if __name__ == "__main__":
    main()
