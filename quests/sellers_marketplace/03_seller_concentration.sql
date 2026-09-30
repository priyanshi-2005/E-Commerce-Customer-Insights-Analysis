
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
