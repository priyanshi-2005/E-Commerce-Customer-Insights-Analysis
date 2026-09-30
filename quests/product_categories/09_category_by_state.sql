
-- Question: Which categories are most popular in each top state?
-- Top 5 states by revenue; category revenue within those states

WITH top_states AS (
    SELECT customer_state
    FROM (
        SELECT customer_state, SUM(item_gmv) AS rev
        FROM v_item_enriched
        GROUP BY customer_state
        ORDER BY rev DESC
        LIMIT 5
    )
)
SELECT
    ie.customer_state,
    ie.category,
    ROUND(SUM(ie.item_gmv), 2) AS revenue
FROM v_item_enriched ie
JOIN top_states ts ON ie.customer_state = ts.customer_state
GROUP BY ie.customer_state, ie.category
ORDER BY ie.customer_state, revenue DESC;
