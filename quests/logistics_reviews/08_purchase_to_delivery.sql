
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
