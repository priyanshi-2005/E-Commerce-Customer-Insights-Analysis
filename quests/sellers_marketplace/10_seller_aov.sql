
-- Question: What is avg order value by top sellers?
-- Top 20 sellers by revenue; AOV at order level for items from that seller

WITH top_sellers AS (
    SELECT seller_id
    FROM (
        SELECT seller_id, SUM(item_gmv) AS revenue
        FROM v_item_enriched
        GROUP BY seller_id
        ORDER BY revenue DESC
        LIMIT 20
    )
),
order_seller AS (
    SELECT ie.seller_id, ie.order_id, SUM(ie.item_gmv) AS order_seller_gmv
    FROM v_item_enriched ie
    JOIN top_sellers ts ON ie.seller_id = ts.seller_id
    GROUP BY ie.seller_id, ie.order_id
),
seller_aov AS (
    SELECT
        seller_id,
        ROUND(AVG(order_seller_gmv), 2) AS avg_order_value
    FROM order_seller
    GROUP BY seller_id
),
ranked AS (
    SELECT seller_id, avg_order_value,
        ROW_NUMBER() OVER (ORDER BY avg_order_value DESC) AS seller_rank
    FROM seller_aov
)
SELECT seller_rank, seller_id, avg_order_value
FROM ranked
ORDER BY seller_rank;
