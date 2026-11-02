-- CONSULTA Q1: Unwind, Filter & Grouping (Saturación de CPU)
-- Experimento IT2iD (2026) - PostgreSQL JSONB
-- 
-- Objetivo: Desanidar el arreglo de ítems mediante jsonb_array_elements,
-- filtrar price > 50, calcular subtotal y agrupar sumatoria y promedio por país y categoría.

SELECT 
    data->'customer'->'geo'->>'country' AS country,
    item->>'category' AS category,
    SUM((item->>'qty')::numeric * (item->>'price')::numeric) AS total_revenue,
    AVG((item->>'qty')::numeric * (item->>'price')::numeric) AS avg_revenue,
    COUNT(*) AS count
FROM 
    orders, 
    jsonb_array_elements(data->'items') AS item
WHERE 
    (item->>'price')::numeric > 50
GROUP BY 
    1, 2;

