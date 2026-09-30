
-- Question: Do products with more photos sell more?

WITH enriched AS (
    SELECT
        ie.item_gmv,
        p.product_photos_qty
    FROM v_item_enriched ie
    JOIN products p ON ie.product_id = p.product_id
),
bucketed AS (
    SELECT
        CASE
            WHEN product_photos_qty IS NULL OR product_photos_qty <= 1 THEN '1 photo'
            WHEN product_photos_qty <= 3 THEN '2-3 photos'
            WHEN product_photos_qty <= 5 THEN '4-5 photos'
            ELSE '6+ photos'
        END AS photo_bucket,
        item_gmv
    FROM enriched
)
SELECT
    photo_bucket,
    ROUND(SUM(item_gmv), 2) AS revenue
FROM bucketed
GROUP BY photo_bucket
ORDER BY photo_bucket;
