
-- Question: How are sellers distributed across states?

SELECT
    seller_state,
    COUNT(DISTINCT seller_id) AS sellers
FROM sellers
GROUP BY seller_state
ORDER BY sellers DESC;
