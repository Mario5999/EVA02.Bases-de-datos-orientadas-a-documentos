-- Q2_SORT_ALL: fuerza una ordenación completa y dependiente del orden,
-- independiente de la consulta Top-1000. El runner establece work_mem y
-- desactiva paralelismo solo para esta variante, haciendo comparable el límite
-- de memoria por sort y evitando que workers oculten el spill.
SELECT COUNT(*), MAX(ordinal), SUM(ordinal * final_total)
FROM (
    SELECT
        ROW_NUMBER() OVER (ORDER BY final_total DESC) AS ordinal,
        final_total
    FROM (
        SELECT (data->'payment'->>'final_total')::numeric AS final_total
        FROM orders
        WHERE data->'payment'->>'status' = 'completed'
          AND (data->>'timestamp')::timestamptz >= '2026-01-01 00:00:00Z'
    ) AS filtered_orders
)
AS ranked_orders;
