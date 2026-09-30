
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
