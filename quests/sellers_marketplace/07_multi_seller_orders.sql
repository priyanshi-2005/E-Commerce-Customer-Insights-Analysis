
-- Question: How many orders involve multiple sellers?

WITH seller_counts AS (
    SELECT order_id, COUNT(DISTINCT seller_id) AS seller_cnt
    FROM v_item_enriched
    GROUP BY order_id
),
tagged AS (
    SELECT
        CASE WHEN seller_cnt > 1 THEN 'Multi-Seller' ELSE 'Single-Seller' END AS order_type,
        order_id,
        seller_cnt
    FROM seller_counts
),
tot AS (SELECT COUNT(*) AS total FROM seller_counts)
SELECT
    order_type,
    COUNT(*) AS orders,
    (SELECT SUM(CASE WHEN seller_cnt > 1 THEN 1 ELSE 0 END) FROM seller_counts) AS multi_seller_orders,
    ROUND(
        (SELECT SUM(CASE WHEN seller_cnt > 1 THEN 1 ELSE 0 END) FROM seller_counts) * 100.0
        / (SELECT total FROM tot),
        2
    ) AS multi_seller_share_pct
FROM tagged
GROUP BY order_type
ORDER BY order_type;
