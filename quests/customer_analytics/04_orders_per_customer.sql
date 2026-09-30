
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
