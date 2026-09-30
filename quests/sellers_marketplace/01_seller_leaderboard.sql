
-- Question: Which sellers drive the most revenue?

WITH seller_rev AS (
    SELECT seller_id, ROUND(SUM(item_gmv), 2) AS revenue
    FROM v_item_enriched
    GROUP BY seller_id
),
ranked AS (
    SELECT seller_id, revenue,
        ROW_NUMBER() OVER (ORDER BY revenue DESC) AS seller_rank
    FROM seller_rev
)
SELECT seller_rank, seller_id, revenue
FROM ranked
WHERE seller_rank <= 20
ORDER BY seller_rank;
