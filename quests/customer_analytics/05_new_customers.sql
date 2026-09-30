
-- Question: How many new customers join each month?
-- First order month per customer

WITH first_order AS (
    SELECT
        customer_unique_id,
        MIN(purchase_month) AS cohort_month
    FROM v_order_revenue
    GROUP BY customer_unique_id
)
SELECT cohort_month, COUNT(*) AS new_customers
FROM first_order
GROUP BY cohort_month
ORDER BY cohort_month;
