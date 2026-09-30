
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
