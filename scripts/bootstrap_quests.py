#!/usr/bin/env python3
"""Write quest SQL files from QUEST_SQL catalog."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTS_DIR = ROOT / "quests"

QUEST_SQL: dict[str, str] = {
    "customer_analytics/01_customer_segments.sql": """
-- Question: How much GMV comes from one-time vs repeat customers?

WITH seg AS (
    SELECT
        customer_id,
        CASE
            WHEN total_orders = 1 THEN 'One-Time'
            WHEN total_orders BETWEEN 2 AND 3 THEN 'Repeat (2-3)'
            ELSE 'Loyal (4+)'
        END AS customer_segment,
        lifetime_gmv
    FROM v_customer_orders
)
SELECT
    customer_segment,
    COUNT(*) AS customers,
    ROUND(SUM(lifetime_gmv), 2) AS segment_gmv
FROM seg
GROUP BY customer_segment
ORDER BY CASE customer_segment WHEN 'One-Time' THEN 1 WHEN 'Repeat (2-3)' THEN 2 ELSE 3 END;
""",

    "customer_analytics/02_ltv_distribution.sql": """
-- Question: What does customer lifetime GMV distribution look like?
-- One row per customer with bucket for histogram aggregation

SELECT
    CASE
        WHEN lifetime_gmv < 100 THEN '< R$100'
        WHEN lifetime_gmv < 250 THEN 'R$100-249'
        WHEN lifetime_gmv < 500 THEN 'R$250-499'
        WHEN lifetime_gmv < 1000 THEN 'R$500-999'
        ELSE 'R$1000+'
    END AS ltv_bucket,
    COUNT(*) AS customers,
    ROUND(AVG(lifetime_gmv), 2) AS lifetime_gmv
FROM v_customer_orders
GROUP BY ltv_bucket
ORDER BY MIN(lifetime_gmv);
""",

    "customer_analytics/03_top_customers.sql": """
-- Question: Who are the top 20 customers by lifetime GMV?

WITH ranked AS (
    SELECT
        customer_id,
        ROUND(lifetime_gmv, 2) AS lifetime_gmv,
        ROW_NUMBER() OVER (ORDER BY lifetime_gmv DESC) AS customer_rank
    FROM v_customer_orders
)
SELECT customer_rank, customer_id, lifetime_gmv
FROM ranked
WHERE customer_rank <= 20
ORDER BY customer_rank;
""",

    "customer_analytics/04_orders_per_customer.sql": """
-- Question: How many orders do most customers place?

SELECT
    CASE
        WHEN total_orders = 1 THEN '1 order'
        WHEN total_orders BETWEEN 2 AND 3 THEN '2-3 orders'
        WHEN total_orders BETWEEN 4 AND 5 THEN '4-5 orders'
        ELSE '6+ orders'
    END AS order_bucket,
    COUNT(*) AS customers
FROM v_customer_orders
GROUP BY order_bucket
ORDER BY CASE order_bucket WHEN '1 order' THEN 1 WHEN '2-3 orders' THEN 2 WHEN '4-5 orders' THEN 3 ELSE 4 END;
""",

    "customer_analytics/05_new_customers.sql": """
-- Question: How many new customers join each month?
-- First order month per customer

WITH first_order AS (
    SELECT
        customer_id,
        MIN(purchase_month) AS cohort_month
    FROM v_order_revenue
    GROUP BY customer_id
)
SELECT cohort_month, COUNT(*) AS new_customers
FROM first_order
GROUP BY cohort_month
ORDER BY cohort_month;
""",

    "customer_analytics/06_repeat_rate_cohort.sql": """
-- Question: What is repeat purchase rate by first-order cohort?

WITH first_order AS (
    SELECT customer_id, MIN(purchase_month) AS cohort_month
    FROM v_order_revenue
    GROUP BY customer_id
),
cohort_stats AS (
    SELECT
        f.cohort_month,
        COUNT(*) AS cohort_customers,
        SUM(CASE WHEN c.total_orders > 1 THEN 1 ELSE 0 END) AS repeat_customers
    FROM first_order f
    JOIN v_customer_orders c ON f.customer_id = c.customer_id
    GROUP BY f.cohort_month
)
SELECT
    cohort_month,
    repeat_customers,
    ROUND(repeat_customers * 100.0 / cohort_customers, 2) AS repeat_rate_pct
FROM cohort_stats
ORDER BY cohort_month;
""",

    "customer_analytics/07_cohort_retention.sql": """
-- Question: How does cohort retention decay over months?

WITH first_order AS (
    SELECT customer_id, MIN(purchase_date) AS first_date
    FROM v_order_revenue
    GROUP BY customer_id
),
activity AS (
    SELECT
        f.customer_id,
        f.first_date,
        CAST(
            (strftime('%Y', v.purchase_date) - strftime('%Y', f.first_date)) * 12
            + (strftime('%m', v.purchase_date) - strftime('%m', f.first_date))
        AS INTEGER) AS months_since_first_order
    FROM first_order f
    JOIN v_order_revenue v ON v.customer_id = f.customer_id
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
        COUNT(DISTINCT a.customer_id) AS active_customers
    FROM activity a
    JOIN first_order fo ON a.customer_id = fo.customer_id
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
""",

    "customer_analytics/08_time_to_second_order.sql": """
-- Question: How long until a customer's second order?

WITH ordered AS (
    SELECT
        customer_id,
        order_purchase_timestamp,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_purchase_timestamp) AS rn
    FROM v_order_revenue
),
pairs AS (
    SELECT
        CAST(julianday(b.order_purchase_timestamp) - julianday(a.order_purchase_timestamp) AS INTEGER) AS days_to_second
    FROM ordered a
    JOIN ordered b ON a.customer_id = b.customer_id AND b.rn = 2
    WHERE a.rn = 1
),
bucketed AS (
    SELECT
        CASE
            WHEN days_to_second <= 7 THEN '0-7 days'
            WHEN days_to_second <= 30 THEN '8-30 days'
            WHEN days_to_second <= 90 THEN '31-90 days'
            ELSE '90+ days'
        END AS days_bucket,
        days_to_second
    FROM pairs
)
SELECT
    days_bucket,
    COUNT(*) AS customers,
    ROUND(AVG(days_to_second * 1.0), 0) AS days_to_second
FROM bucketed
GROUP BY days_bucket
ORDER BY MIN(days_to_second);
""",

    "customer_analytics/09_customers_by_state.sql": """
-- Question: Which states have the most customers?

SELECT
    customer_state,
    COUNT(DISTINCT customer_id) AS customers
FROM v_item_enriched
GROUP BY customer_state
ORDER BY customers DESC;
""",

    "customer_analytics/10_churn_proxy.sql": """
-- Question: How many customers have not ordered in 6+ months?
-- Churn proxy: no order in 180 days before max purchase date

WITH bounds AS (
    SELECT MAX(purchase_date) AS max_date FROM v_order_revenue
),
last_active AS (
    SELECT customer_id, MAX(purchase_date) AS last_order_date
    FROM v_order_revenue
    GROUP BY customer_id
),
tagged AS (
    SELECT
        customer_id,
        CASE
            WHEN julianday((SELECT max_date FROM bounds)) - julianday(last_order_date) > 180
            THEN 'Churned Proxy'
            ELSE 'Active'
        END AS status
    FROM last_active
),
tot AS (SELECT COUNT(*) AS total FROM tagged)
SELECT
    status,
    COUNT(*) AS customers,
    ROUND(
        SUM(CASE WHEN status = 'Churned Proxy' THEN 1 ELSE 0 END) * 100.0 / (SELECT total FROM tot),
        2
    ) AS churn_rate_pct
FROM tagged
GROUP BY status
ORDER BY CASE status WHEN 'Churned Proxy' THEN 1 ELSE 2 END;
""",

    "logistics_reviews/01_order_status.sql": """
-- Question: What is the order status distribution?

WITH status_counts AS (
    SELECT order_status, COUNT(*) AS orders
    FROM orders
    GROUP BY order_status
),
tot AS (SELECT SUM(orders) AS total FROM status_counts)
SELECT
    order_status,
    orders,
    ROUND(orders * 100.0 / (SELECT total FROM tot), 2) AS share_pct
FROM status_counts
ORDER BY orders DESC;
""",

    "logistics_reviews/02_delay_vs_reviews.sql": """
-- Question: Does late delivery hurt review scores?

WITH delivery AS (
    SELECT
        o.order_id,
        CAST(
            julianday(o.order_delivered_customer_date) - julianday(o.order_estimated_delivery_date)
        AS INTEGER) AS delay_days,
        r.review_score
    FROM orders o
    JOIN order_reviews r ON o.order_id = r.order_id
    WHERE o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
      AND r.review_score IS NOT NULL
)
SELECT
    CASE
        WHEN delay_days <= 0 THEN 'on_time_or_early'
        WHEN delay_days BETWEEN 1 AND 3 THEN 'slight_delay'
        WHEN delay_days BETWEEN 4 AND 7 THEN 'moderate_delay'
        ELSE 'severe_delay'
    END AS delay_bucket,
    COUNT(*) AS reviews,
    ROUND(AVG(review_score), 2) AS avg_review_score
FROM delivery
GROUP BY delay_bucket
ORDER BY avg_review_score DESC;
""",

    "logistics_reviews/03_on_time_rate.sql": """
-- Question: What is the on-time delivery rate?

WITH delivered AS (
    SELECT
        order_id,
        CAST(
            julianday(order_delivered_customer_date) - julianday(order_estimated_delivery_date)
        AS INTEGER) AS delay_days
    FROM orders
    WHERE order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
),
tagged AS (
    SELECT
        CASE WHEN delay_days <= 0 THEN 'On Time' ELSE 'Late' END AS delivery_result,
        order_id,
        delay_days
    FROM delivered
),
tot AS (
    SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN delay_days > 0 THEN 1 ELSE 0 END) AS late_deliveries
    FROM delivered
)
SELECT
    t.delivery_result,
    COUNT(*) AS orders,
    ROUND((SELECT SUM(CASE WHEN delay_days <= 0 THEN 1 ELSE 0 END) FROM delivered) * 100.0 / (SELECT total FROM tot), 2) AS on_time_rate_pct,
    (SELECT late_deliveries FROM tot) AS late_deliveries
FROM tagged t
GROUP BY t.delivery_result
ORDER BY t.delivery_result;
""",

    "logistics_reviews/04_avg_delay_days.sql": """
-- Question: How many days late are deliveries on average?
-- Only late orders; average by customer state

WITH late AS (
    SELECT
        o.order_id,
        c.customer_state,
        CAST(
            julianday(o.order_delivered_customer_date) - julianday(o.order_estimated_delivery_date)
        AS INTEGER) AS delay_days
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
      AND julianday(o.order_delivered_customer_date) > julianday(o.order_estimated_delivery_date)
)
SELECT
    customer_state,
    COUNT(*) AS orders,
    ROUND(AVG(delay_days * 1.0), 2) AS avg_delay_days
FROM late
GROUP BY customer_state
HAVING COUNT(*) >= 50
ORDER BY avg_delay_days DESC
LIMIT 20;
""",

    "logistics_reviews/05_review_distribution.sql": """
-- Question: What is the review score distribution?

WITH scores AS (
    SELECT review_score, COUNT(*) AS reviews
    FROM order_reviews
    WHERE review_score IS NOT NULL
    GROUP BY review_score
),
tot AS (SELECT SUM(reviews) AS total FROM scores)
SELECT
    review_score,
    reviews,
    ROUND(reviews * 100.0 / (SELECT total FROM tot), 2) AS share_pct
FROM scores
ORDER BY review_score;
""",

    "logistics_reviews/06_low_score_categories.sql": """
-- Question: Which categories get the lowest review scores?

SELECT
    ie.category,
    COUNT(DISTINCT r.order_id) AS orders,
    ROUND(AVG(r.review_score * 1.0), 2) AS avg_review_score
FROM order_reviews r
JOIN v_item_enriched ie ON r.order_id = ie.order_id
WHERE r.review_score IS NOT NULL
GROUP BY ie.category
HAVING COUNT(DISTINCT r.order_id) >= 100
ORDER BY avg_review_score ASC
LIMIT 15;
""",

    "logistics_reviews/07_review_coverage.sql": """
-- Question: What share of delivered orders get reviewed?

WITH delivered AS (
    SELECT
        order_id,
        strftime('%Y-%m', order_delivered_customer_date) AS month
    FROM orders
    WHERE order_status = 'delivered'
      AND order_delivered_customer_date IS NOT NULL
),
coverage AS (
    SELECT
        d.month,
        COUNT(DISTINCT d.order_id) AS delivered_orders,
        COUNT(DISTINCT r.order_id) AS reviewed_orders
    FROM delivered d
    LEFT JOIN order_reviews r ON d.order_id = r.order_id
    GROUP BY d.month
)
SELECT
    month,
    reviewed_orders,
    delivered_orders,
    ROUND(reviewed_orders * 100.0 / NULLIF(delivered_orders, 0), 2) AS review_coverage_pct
FROM coverage
ORDER BY month;
""",

    "logistics_reviews/08_purchase_to_delivery.sql": """
-- Question: How long from purchase to delivery?

WITH delivery AS (
    SELECT
        order_id,
        CAST(
            julianday(order_delivered_customer_date) - julianday(order_purchase_timestamp)
        AS INTEGER) AS delivery_days
    FROM orders
    WHERE order_delivered_customer_date IS NOT NULL
      AND order_purchase_timestamp IS NOT NULL
),
overall_median AS (
    SELECT ROUND(AVG(delivery_days * 1.0), 0) AS median_delivery_days
    FROM (
        SELECT delivery_days,
            ROW_NUMBER() OVER (ORDER BY delivery_days) AS rn,
            COUNT(*) OVER () AS cnt
        FROM delivery
    )
    WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
)
SELECT
    CASE
        WHEN delivery_days <= 3 THEN '0-3 days'
        WHEN delivery_days <= 7 THEN '4-7 days'
        WHEN delivery_days <= 14 THEN '8-14 days'
        WHEN delivery_days <= 21 THEN '15-21 days'
        ELSE '22+ days'
    END AS delivery_days_bucket,
    COUNT(*) AS orders,
    (SELECT median_delivery_days FROM overall_median) AS median_delivery_days
FROM delivery
GROUP BY delivery_days_bucket
ORDER BY MIN(delivery_days);
""",

    "logistics_reviews/09_delay_by_month.sql": """
-- Question: Which months had the worst delivery delays?

WITH late AS (
    SELECT
        strftime('%Y-%m', order_purchase_timestamp) AS purchase_month,
        CAST(
            julianday(order_delivered_customer_date) - julianday(order_estimated_delivery_date)
        AS INTEGER) AS delay_days
    FROM orders
    WHERE order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
      AND julianday(order_delivered_customer_date) > julianday(order_estimated_delivery_date)
)
SELECT
    purchase_month,
    COUNT(*) AS late_orders,
    ROUND(AVG(delay_days * 1.0), 2) AS avg_delay_days
FROM late
GROUP BY purchase_month
ORDER BY purchase_month;
""",

    "logistics_reviews/10_review_score_trend.sql": """
-- Question: Do review scores trend down over time?

SELECT
    strftime('%Y-%m', review_creation_date) AS review_month,
    COUNT(*) AS reviews,
    ROUND(AVG(review_score * 1.0), 2) AS avg_review_score
FROM order_reviews
WHERE review_score IS NOT NULL
  AND review_creation_date IS NOT NULL
GROUP BY review_month
ORDER BY review_month;
""",

    "payments_checkout/01_payment_mix_orders.sql": """
-- Question: What is the payment type mix by order count?

SELECT payment_type, COUNT(DISTINCT order_id) AS orders
FROM order_payments
GROUP BY payment_type
ORDER BY orders DESC;
""",

    "payments_checkout/02_payment_mix_value.sql": """
-- Question: What is the payment type mix by value?

WITH by_type AS (
    SELECT payment_type, ROUND(SUM(payment_value), 2) AS total_payment_value
    FROM order_payments
    GROUP BY payment_type
),
tot AS (SELECT SUM(total_payment_value) AS total FROM by_type)
SELECT
    payment_type,
    total_payment_value,
    ROUND(total_payment_value * 100.0 / (SELECT total FROM tot), 2) AS value_share_pct
FROM by_type
ORDER BY total_payment_value DESC;
""",

    "payments_checkout/03_payment_aov.sql": """
-- Question: Which payment types have the highest AOV?
-- Primary payment type per order (highest payment_value)

WITH primary_pay AS (
    SELECT order_id, payment_type
    FROM (
        SELECT
            order_id,
            payment_type,
            ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY payment_value DESC) AS rn
        FROM order_payments
    )
    WHERE rn = 1
)
SELECT
    pp.payment_type,
    ROUND(AVG(v.order_gmv), 2) AS avg_order_value
FROM primary_pay pp
JOIN v_order_revenue v ON pp.order_id = v.order_id
GROUP BY pp.payment_type
ORDER BY avg_order_value DESC;
""",

    "payments_checkout/04_installments.sql": """
-- Question: How are installment plans distributed?
-- Uses max installments per order

WITH per_order AS (
    SELECT order_id, MAX(payment_installments) AS payment_installments
    FROM order_payments
    GROUP BY order_id
)
SELECT
    payment_installments,
    COUNT(*) AS orders,
    ROUND(AVG(payment_installments * 1.0), 2) AS avg_installments
FROM per_order
GROUP BY payment_installments
ORDER BY payment_installments;
""",

    "payments_checkout/05_multi_payment_orders.sql": """
-- Question: How many orders use multiple payment methods?

WITH pay_counts AS (
    SELECT order_id, COUNT(*) AS payment_rows
    FROM order_payments
    GROUP BY order_id
),
tagged AS (
    SELECT
        CASE WHEN payment_rows > 1 THEN 'Multi Payment' ELSE 'Single Payment' END AS payment_pattern,
        order_id
    FROM pay_counts
),
tot AS (SELECT COUNT(*) AS total_orders FROM pay_counts)
SELECT
    payment_pattern,
    COUNT(*) AS orders,
    (SELECT SUM(CASE WHEN payment_rows > 1 THEN 1 ELSE 0 END) FROM pay_counts) AS multi_payment_orders,
    ROUND(
        (SELECT SUM(CASE WHEN payment_rows > 1 THEN 1 ELSE 0 END) FROM pay_counts) * 100.0
        / (SELECT total_orders FROM tot),
        2
    ) AS multi_payment_share_pct
FROM tagged
GROUP BY payment_pattern
ORDER BY payment_pattern;
""",

    "payments_checkout/06_unapproved_orders.sql": """
-- Question: What share of orders never get approved?

SELECT
    purchase_month,
    COUNT(*) AS orders,
    ROUND(
        SUM(CASE WHEN o.order_approved_at IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    ) AS unapproved_rate_pct
FROM v_order_revenue v
JOIN orders o ON v.order_id = o.order_id
GROUP BY purchase_month
ORDER BY purchase_month;
""",

    "payments_checkout/07_payment_by_state.sql": """
-- Question: Which states prefer credit card vs boleto?
-- Top 5 states by order count

WITH top_states AS (
    SELECT customer_state
    FROM (
        SELECT customer_state, COUNT(DISTINCT order_id) AS orders
        FROM v_item_enriched
        GROUP BY customer_state
        ORDER BY orders DESC
        LIMIT 5
    )
)
SELECT
    ie.customer_state,
    op.payment_type,
    COUNT(DISTINCT op.order_id) AS orders
FROM order_payments op
JOIN v_item_enriched ie ON op.order_id = ie.order_id
JOIN top_states ts ON ie.customer_state = ts.customer_state
GROUP BY ie.customer_state, op.payment_type
ORDER BY ie.customer_state, orders DESC;
""",

    "payments_checkout/08_credit_card_trend.sql": """
-- Question: Is credit card share increasing over time?

WITH monthly AS (
    SELECT
        v.purchase_month,
        COUNT(DISTINCT v.order_id) AS total_orders,
        COUNT(DISTINCT CASE WHEN op.payment_type = 'credit_card' THEN op.order_id END) AS cc_orders
    FROM v_order_revenue v
    LEFT JOIN order_payments op ON v.order_id = op.order_id
    GROUP BY v.purchase_month
)
SELECT
    purchase_month,
    cc_orders,
    total_orders,
    ROUND(cc_orders * 100.0 / NULLIF(total_orders, 0), 2) AS credit_card_share_pct
FROM monthly
ORDER BY purchase_month;
""",

    "payments_checkout/09_high_value_payment.sql": """
-- Question: Do high-value orders prefer credit card?
-- Top quartile orders by GMV

WITH ranked AS (
    SELECT order_id, order_gmv,
        NTILE(4) OVER (ORDER BY order_gmv DESC) AS quartile
    FROM v_order_revenue
),
threshold AS (
    SELECT ROUND(MIN(order_gmv), 2) AS gmv_threshold FROM ranked WHERE quartile = 1
),
high AS (
    SELECT order_id FROM ranked WHERE quartile = 1
),
stats AS (
    SELECT
        COUNT(DISTINCT h.order_id) AS high_orders,
        COUNT(DISTINCT CASE WHEN op.payment_type = 'credit_card' THEN h.order_id END) AS cc_orders
    FROM high h
    LEFT JOIN order_payments op ON h.order_id = op.order_id
)
SELECT
    'top_quartile' AS order_value_tier,
    (SELECT gmv_threshold FROM threshold) AS gmv_threshold,
    ROUND((SELECT cc_orders FROM stats) * 100.0 / NULLIF((SELECT high_orders FROM stats), 0), 2) AS credit_card_share_pct;
""",

    "payments_checkout/10_payment_value_trend.sql": """
-- Question: What is average payment value by type and month?
-- Overall avg payment value per month (all types)

SELECT
    strftime('%Y-%m', o.order_purchase_timestamp) AS purchase_month,
    op.payment_type,
    ROUND(AVG(op.payment_value), 2) AS avg_payment_value
FROM order_payments op
JOIN orders o ON op.order_id = o.order_id
GROUP BY purchase_month, op.payment_type
ORDER BY purchase_month, op.payment_type;
""",

    "product_categories/01_top_categories_revenue.sql": """
-- Question: Which categories drive the most revenue?

WITH cat AS (
    SELECT category, ROUND(SUM(item_gmv), 2) AS revenue
    FROM v_item_enriched
    GROUP BY category
),
tot AS (SELECT SUM(revenue) AS total_revenue FROM cat)
SELECT
    category,
    revenue,
    ROUND(revenue * 100.0 / (SELECT total_revenue FROM tot), 2) AS revenue_share_pct
FROM cat
ORDER BY revenue DESC
LIMIT 15;
""",

    "product_categories/02_top_categories_orders.sql": """
-- Question: Which categories get the most orders?
-- Distinct order_id per category

SELECT
    category,
    COUNT(DISTINCT order_id) AS orders
FROM v_item_enriched
GROUP BY category
ORDER BY orders DESC
LIMIT 15;
""",

    "product_categories/03_category_aov.sql": """
-- Question: Which categories have the highest AOV?
-- Average item GMV by category

SELECT
    category,
    ROUND(AVG(item_gmv), 2) AS avg_order_value
FROM v_item_enriched
GROUP BY category
ORDER BY avg_order_value DESC
LIMIT 15;
""",

    "product_categories/04_items_per_order.sql": """
-- Question: How many items are sold per order by category?

WITH oc AS (
    SELECT category, order_id, COUNT(*) AS items_in_order
    FROM v_item_enriched
    GROUP BY category, order_id
)
SELECT
    category,
    ROUND(AVG(items_in_order * 1.0), 2) AS avg_items_per_order
FROM oc
GROUP BY category
ORDER BY avg_items_per_order DESC
LIMIT 15;
""",

    "product_categories/05_category_growth.sql": """
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
""",

    "product_categories/06_bottom_categories.sql": """
-- Question: Which categories underperform on revenue share?

WITH cat AS (
    SELECT category, ROUND(SUM(item_gmv), 2) AS revenue
    FROM v_item_enriched
    GROUP BY category
),
tot AS (SELECT SUM(revenue) AS total_revenue FROM cat)
SELECT
    category,
    revenue,
    ROUND(revenue * 100.0 / (SELECT total_revenue FROM tot), 2) AS revenue_share_pct
FROM cat
ORDER BY revenue_share_pct ASC
LIMIT 15;
""",

    "product_categories/07_freight_by_category.sql": """
-- Question: What is freight revenue by category?

SELECT
    category,
    ROUND(SUM(freight_value), 2) AS freight_revenue
FROM v_item_enriched
GROUP BY category
ORDER BY freight_revenue DESC
LIMIT 15;
""",

    "product_categories/08_photos_vs_sales.sql": """
-- Question: Do products with more photos sell more?

WITH enriched AS (
    SELECT
        ie.item_gmv,
        p.product_photos_qty
    FROM v_item_enriched ie
    JOIN products p ON ie.product_id = p.product_id
),
bucketed AS (
    SELECT
        CASE
            WHEN product_photos_qty IS NULL OR product_photos_qty <= 1 THEN '1 photo'
            WHEN product_photos_qty <= 3 THEN '2-3 photos'
            WHEN product_photos_qty <= 5 THEN '4-5 photos'
            ELSE '6+ photos'
        END AS photo_bucket,
        item_gmv
    FROM enriched
)
SELECT
    photo_bucket,
    ROUND(SUM(item_gmv), 2) AS revenue
FROM bucketed
GROUP BY photo_bucket
ORDER BY photo_bucket;
""",

    "product_categories/09_category_by_state.sql": """
-- Question: Which categories are most popular in each top state?
-- Top 5 states by revenue; category revenue within those states

WITH top_states AS (
    SELECT customer_state
    FROM (
        SELECT customer_state, SUM(item_gmv) AS rev
        FROM v_item_enriched
        GROUP BY customer_state
        ORDER BY rev DESC
        LIMIT 5
    )
)
SELECT
    ie.customer_state,
    ie.category,
    ROUND(SUM(ie.item_gmv), 2) AS revenue
FROM v_item_enriched ie
JOIN top_states ts ON ie.customer_state = ts.customer_state
GROUP BY ie.customer_state, ie.category
ORDER BY ie.customer_state, revenue DESC;
""",

    "product_categories/10_price_distribution.sql": """
-- Question: What is the price distribution by category?
-- Median item price per category

WITH ranked AS (
    SELECT
        category,
        price,
        ROW_NUMBER() OVER (PARTITION BY category ORDER BY price) AS rn,
        COUNT(*) OVER (PARTITION BY category) AS cnt
    FROM v_item_enriched
)
SELECT
    category,
    ROUND(AVG(price), 2) AS median_price
FROM ranked
WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
GROUP BY category
ORDER BY median_price DESC
LIMIT 15;
""",

    "revenue_growth/01_monthly_gmv.sql": """
-- Question: How does monthly GMV trend over time?
-- Grain: one row per purchase month

SELECT
    purchase_month,
    COUNT(DISTINCT order_id) AS orders,
    ROUND(SUM(order_gmv), 2) AS gmv
FROM v_order_revenue
GROUP BY purchase_month
ORDER BY purchase_month;
""",

    "revenue_growth/02_mom_growth.sql": """
-- Question: What is the month-over-month GMV growth rate?
-- Grain: one row per month; first month has NULL mom_growth_pct

WITH monthly AS (
    SELECT
        purchase_month,
        ROUND(SUM(order_gmv), 2) AS gmv
    FROM v_order_revenue
    GROUP BY purchase_month
),
with_lag AS (
    SELECT
        purchase_month,
        gmv,
        LAG(gmv) OVER (ORDER BY purchase_month) AS prev_gmv
    FROM monthly
)
SELECT
    purchase_month,
    gmv,
    ROUND(
        CASE
            WHEN prev_gmv IS NULL OR prev_gmv = 0 THEN NULL
            ELSE (gmv - prev_gmv) * 100.0 / prev_gmv
        END,
        2
    ) AS mom_growth_pct
FROM with_lag
ORDER BY purchase_month;
""",

    "revenue_growth/03_monthly_aov.sql": """
-- Question: How does average order value change monthly?
-- Grain: one row per purchase month

SELECT
    purchase_month,
    ROUND(SUM(order_gmv) * 1.0 / COUNT(DISTINCT order_id), 2) AS avg_order_value
FROM v_order_revenue
GROUP BY purchase_month
ORDER BY purchase_month;
""",

    "revenue_growth/04_revenue_split.sql": """
-- Question: What is the split between product revenue and freight?
-- Grain: one row per purchase month

SELECT
    purchase_month,
    ROUND(SUM(product_revenue), 2) AS product_revenue,
    ROUND(SUM(freight_revenue), 2) AS freight_revenue,
    ROUND(
        SUM(freight_revenue) * 100.0 / NULLIF(SUM(product_revenue) + SUM(freight_revenue), 0),
        2
    ) AS freight_share_pct
FROM v_order_revenue
GROUP BY purchase_month
ORDER BY purchase_month;
""",

    "revenue_growth/05_revenue_by_state.sql": """
-- Question: Which states generate the most revenue?
-- Grain: one row per customer state

WITH state_rev AS (
    SELECT
        c.customer_state,
        ROUND(SUM(v.order_gmv), 2) AS revenue
    FROM v_order_revenue v
    JOIN orders o ON v.order_id = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY c.customer_state
),
tot AS (
    SELECT SUM(revenue) AS total_revenue FROM state_rev
)
SELECT
    customer_state,
    revenue,
    ROUND(revenue * 100.0 / (SELECT total_revenue FROM tot), 2) AS revenue_share_pct
FROM state_rev
ORDER BY revenue DESC;
""",

    "revenue_growth/06_peak_orders.sql": """
-- Question: Which month had the highest order volume?
-- Grain: one row per purchase month

SELECT
    purchase_month,
    COUNT(DISTINCT order_id) AS orders,
    ROUND(SUM(order_gmv), 2) AS gmv
FROM v_order_revenue
GROUP BY purchase_month
ORDER BY purchase_month;
""",

    "revenue_growth/07_weekday_weekend.sql": """
-- Question: Do weekdays or weekends drive more orders?
-- Grain: weekday vs weekend (ordered weekday first)

WITH tagged AS (
    SELECT
        order_id,
        CASE
            WHEN CAST(strftime('%w', order_purchase_timestamp) AS INTEGER) IN (0, 6) THEN 'Weekend'
            ELSE 'Weekday'
        END AS day_type
    FROM v_order_revenue
),
agg AS (
    SELECT day_type, COUNT(DISTINCT order_id) AS orders
    FROM tagged
    GROUP BY day_type
),
tot AS (
    SELECT SUM(orders) AS total_orders FROM agg
)
SELECT
    day_type,
    orders,
    ROUND(orders * 100.0 / (SELECT total_orders FROM tot), 2) AS order_share_pct
FROM agg
ORDER BY CASE day_type WHEN 'Weekday' THEN 1 ELSE 2 END;
""",

    "revenue_growth/08_gmv_concentration.sql": """
-- Question: What share of GMV comes from the top 10% of orders?
-- Top decile by order GMV vs remainder

WITH ranked AS (
    SELECT
        order_id,
        order_gmv,
        NTILE(10) OVER (ORDER BY order_gmv DESC) AS decile
    FROM v_order_revenue
),
segmented AS (
    SELECT
        CASE WHEN decile = 1 THEN 'top_10_pct_orders' ELSE 'other_90_pct_orders' END AS segment,
        SUM(order_gmv) AS gmv
    FROM ranked
    GROUP BY 1
),
tot AS (
    SELECT SUM(order_gmv) AS total_gmv, COUNT(*) AS total_orders FROM v_order_revenue
)
SELECT
    s.segment,
    ROUND(s.gmv, 2) AS gmv,
    ROUND(
        (SELECT gmv FROM segmented WHERE segment = 'top_10_pct_orders') * 100.0
        / (SELECT total_gmv FROM tot),
        2
    ) AS top_decile_gmv_share_pct,
    ROUND((SELECT total_gmv FROM tot), 2) AS total_gmv,
    (SELECT total_orders FROM tot) AS total_orders
FROM segmented s
ORDER BY CASE s.segment WHEN 'top_10_pct_orders' THEN 1 ELSE 2 END;
""",

    "revenue_growth/09_cumulative_gmv.sql": """
-- Question: What is the cumulative GMV curve by month?
-- Includes months_to_half on the row where cumulative GMV first reaches 50%

WITH monthly AS (
    SELECT
        purchase_month,
        ROUND(SUM(order_gmv), 2) AS monthly_gmv
    FROM v_order_revenue
    GROUP BY purchase_month
),
cum AS (
    SELECT
        purchase_month,
        monthly_gmv,
        SUM(monthly_gmv) OVER (ORDER BY purchase_month) AS cumulative_gmv,
        SUM(monthly_gmv) OVER () AS total_gmv
    FROM monthly
),
half AS (
    SELECT MIN(purchase_month) AS months_to_half
    FROM cum
    WHERE cumulative_gmv >= total_gmv * 0.5
)
SELECT
    c.purchase_month,
    c.monthly_gmv,
    ROUND(c.cumulative_gmv, 2) AS cumulative_gmv,
    (SELECT COUNT(*) FROM monthly m WHERE m.purchase_month <= (SELECT months_to_half FROM half)) AS months_to_half
FROM cum c
ORDER BY c.purchase_month;
""",

    "revenue_growth/10_orders_gmv_corr.sql": """
-- Question: How do order count and GMV correlate monthly?
-- Pearson correlation across monthly aggregates

WITH monthly AS (
    SELECT
        purchase_month,
        COUNT(DISTINCT order_id) AS orders,
        SUM(order_gmv) AS gmv
    FROM v_order_revenue
    GROUP BY purchase_month
),
stats AS (
    SELECT
        AVG(orders * 1.0) AS mean_o,
        AVG(gmv) AS mean_g,
        AVG(orders * orders * 1.0) AS mean_o2,
        AVG(gmv * gmv) AS mean_g2,
        AVG(orders * gmv * 1.0) AS mean_og
    FROM monthly
)
SELECT
    m.purchase_month,
    m.orders,
    ROUND(m.gmv, 2) AS gmv,
    ROUND(
        (s.mean_og - s.mean_o * s.mean_g)
        / NULLIF(
            SQRT(s.mean_o2 - s.mean_o * s.mean_o)
            * SQRT(s.mean_g2 - s.mean_g * s.mean_g),
            0
        ),
        4
    ) AS orders_gmv_corr
FROM monthly m
CROSS JOIN stats s
ORDER BY m.purchase_month;
""",

    "sellers_marketplace/01_seller_leaderboard.sql": """
-- Question: Which sellers drive the most revenue?

WITH seller_rev AS (
    SELECT seller_id, ROUND(SUM(item_gmv), 2) AS revenue
    FROM v_item_enriched
    GROUP BY seller_id
),
ranked AS (
    SELECT seller_id, revenue,
        ROW_NUMBER() OVER (ORDER BY revenue DESC) AS seller_rank
    FROM seller_rev
)
SELECT seller_rank, seller_id, revenue
FROM ranked
WHERE seller_rank <= 20
ORDER BY seller_rank;
""",

    "sellers_marketplace/02_sellers_by_state.sql": """
-- Question: How are sellers distributed across states?

SELECT
    seller_state,
    COUNT(DISTINCT seller_id) AS sellers
FROM sellers
GROUP BY seller_state
ORDER BY sellers DESC;
""",

    "sellers_marketplace/03_seller_concentration.sql": """
-- Question: What does seller revenue concentration look like?

WITH seller_rev AS (
    SELECT seller_id, SUM(item_gmv) AS revenue
    FROM v_item_enriched
    GROUP BY seller_id
),
ranked AS (
    SELECT seller_id, revenue,
        NTILE(10) OVER (ORDER BY revenue DESC) AS decile
    FROM seller_rev
),
segmented AS (
    SELECT
        CASE WHEN decile = 1 THEN 'top_10_pct_sellers' ELSE 'other_90_pct_sellers' END AS segment,
        SUM(revenue) AS revenue
    FROM ranked
    GROUP BY 1
),
tot AS (SELECT COUNT(*) AS total_sellers, SUM(revenue) AS total_revenue FROM seller_rev)
SELECT
    s.segment,
    ROUND(s.revenue, 2) AS revenue,
    ROUND(
        (SELECT revenue FROM segmented WHERE segment = 'top_10_pct_sellers') * 100.0
        / (SELECT total_revenue FROM tot),
        2
    ) AS top_decile_share_pct,
    (SELECT total_sellers FROM tot) AS total_sellers
FROM segmented s
ORDER BY CASE s.segment WHEN 'top_10_pct_sellers' THEN 1 ELSE 2 END;
""",

    "sellers_marketplace/04_top_seller_categories.sql": """
-- Question: What categories do top sellers focus on?
-- Top 10 sellers by revenue

WITH top_sellers AS (
    SELECT seller_id
    FROM (
        SELECT seller_id, SUM(item_gmv) AS revenue
        FROM v_item_enriched
        GROUP BY seller_id
        ORDER BY revenue DESC
        LIMIT 10
    )
)
SELECT
    ie.category,
    ROUND(SUM(ie.item_gmv), 2) AS revenue
FROM v_item_enriched ie
JOIN top_sellers ts ON ie.seller_id = ts.seller_id
GROUP BY ie.category
ORDER BY revenue DESC
LIMIT 15;
""",

    "sellers_marketplace/05_avg_seller_revenue.sql": """
-- Question: What is the average revenue per seller?

WITH seller_rev AS (
    SELECT seller_id, SUM(item_gmv) AS revenue
    FROM v_item_enriched
    GROUP BY seller_id
)
SELECT
    CASE
        WHEN revenue < 1000 THEN '< R$1k'
        WHEN revenue < 5000 THEN 'R$1k-5k'
        WHEN revenue < 20000 THEN 'R$5k-20k'
        WHEN revenue < 50000 THEN 'R$20k-50k'
        ELSE 'R$50k+'
    END AS revenue_bucket,
    COUNT(*) AS sellers,
    ROUND(AVG(revenue), 2) AS revenue
FROM seller_rev
GROUP BY revenue_bucket
ORDER BY MIN(revenue);
""",

    "sellers_marketplace/06_seller_freight.sql": """
-- Question: Which sellers have the highest freight charges?

SELECT
    seller_id,
    ROUND(SUM(freight_value), 2) AS freight_revenue
FROM v_item_enriched
GROUP BY seller_id
ORDER BY freight_revenue DESC
LIMIT 15;
""",

    "sellers_marketplace/07_multi_seller_orders.sql": """
-- Question: How many orders involve multiple sellers?

WITH seller_counts AS (
    SELECT order_id, COUNT(DISTINCT seller_id) AS seller_cnt
    FROM v_item_enriched
    GROUP BY order_id
),
tagged AS (
    SELECT
        CASE WHEN seller_cnt > 1 THEN 'Multi-Seller' ELSE 'Single-Seller' END AS order_type,
        order_id,
        seller_cnt
    FROM seller_counts
),
tot AS (SELECT COUNT(*) AS total FROM seller_counts)
SELECT
    order_type,
    COUNT(*) AS orders,
    (SELECT SUM(CASE WHEN seller_cnt > 1 THEN 1 ELSE 0 END) FROM seller_counts) AS multi_seller_orders,
    ROUND(
        (SELECT SUM(CASE WHEN seller_cnt > 1 THEN 1 ELSE 0 END) FROM seller_counts) * 100.0
        / (SELECT total FROM tot),
        2
    ) AS multi_seller_share_pct
FROM tagged
GROUP BY order_type
ORDER BY order_type;
""",

    "sellers_marketplace/08_seller_city_gmv.sql": """
-- Question: Which seller cities dominate GMV?

SELECT
    s.seller_city,
    ROUND(SUM(ie.item_gmv), 2) AS revenue
FROM v_item_enriched ie
JOIN sellers s ON ie.seller_id = s.seller_id
GROUP BY s.seller_city
ORDER BY revenue DESC
LIMIT 15;
""",

    "sellers_marketplace/09_long_tail_sellers.sql": """
-- Question: How many sellers are long-tail (low revenue)?
-- Bottom 80% of sellers by cumulative revenue share

WITH seller_rev AS (
    SELECT seller_id, SUM(item_gmv) AS revenue
    FROM v_item_enriched
    GROUP BY seller_id
),
ranked AS (
    SELECT
        seller_id,
        revenue,
        SUM(revenue) OVER (ORDER BY revenue DESC) AS cum_revenue,
        SUM(revenue) OVER () AS total_revenue
    FROM seller_rev
),
tiered AS (
    SELECT
        CASE
            WHEN cum_revenue <= total_revenue * 0.2 THEN 'Head (top 20% GMV)'
            ELSE 'Long Tail (bottom 80% GMV)'
        END AS seller_tier,
        seller_id
    FROM ranked
),
tot AS (SELECT COUNT(*) AS total_sellers FROM seller_rev)
SELECT
    seller_tier,
    COUNT(*) AS sellers,
    ROUND(COUNT(*) * 100.0 / (SELECT total_sellers FROM tot), 2) AS seller_share_pct
FROM tiered
GROUP BY seller_tier
ORDER BY seller_tier;
""",

    "sellers_marketplace/10_seller_aov.sql": """
-- Question: What is avg order value by top sellers?
-- Top 20 sellers by revenue; AOV at order level for items from that seller

WITH top_sellers AS (
    SELECT seller_id
    FROM (
        SELECT seller_id, SUM(item_gmv) AS revenue
        FROM v_item_enriched
        GROUP BY seller_id
        ORDER BY revenue DESC
        LIMIT 20
    )
),
order_seller AS (
    SELECT ie.seller_id, ie.order_id, SUM(ie.item_gmv) AS order_seller_gmv
    FROM v_item_enriched ie
    JOIN top_sellers ts ON ie.seller_id = ts.seller_id
    GROUP BY ie.seller_id, ie.order_id
),
seller_aov AS (
    SELECT
        seller_id,
        ROUND(AVG(order_seller_gmv), 2) AS avg_order_value
    FROM order_seller
    GROUP BY seller_id
),
ranked AS (
    SELECT seller_id, avg_order_value,
        ROW_NUMBER() OVER (ORDER BY avg_order_value DESC) AS seller_rank
    FROM seller_aov
)
SELECT seller_rank, seller_id, avg_order_value
FROM ranked
ORDER BY seller_rank;
""",

}


def main() -> None:
    written = 0
    for rel_path, sql in QUEST_SQL.items():
        out = QUESTS_DIR / rel_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(sql if sql.endswith("\n") else sql + "\n", encoding="utf-8")
        written += 1
    print(f"Wrote {written} quest SQL files under {QUESTS_DIR}")


if __name__ == "__main__":
    main()

