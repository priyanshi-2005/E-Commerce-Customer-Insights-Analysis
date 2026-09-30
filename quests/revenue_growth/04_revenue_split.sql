
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
