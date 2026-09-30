
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
