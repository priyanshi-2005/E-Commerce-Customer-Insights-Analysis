
-- Question: How much GMV comes from one-time vs repeat customers?

WITH seg AS (
    SELECT
        customer_unique_id,
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
