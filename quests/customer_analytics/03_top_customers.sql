
-- Question: Who are the top 20 customers by lifetime GMV?

WITH ranked AS (
    SELECT
        customer_unique_id,
        ROUND(lifetime_gmv, 2) AS lifetime_gmv,
        ROW_NUMBER() OVER (ORDER BY lifetime_gmv DESC) AS customer_rank
    FROM v_customer_orders
)
SELECT customer_rank, customer_unique_id, lifetime_gmv
FROM ranked
WHERE customer_rank <= 20
ORDER BY customer_rank;
