-- CONSULTA Q2: Massive Sort & Top-K (Estrés de Buffer de Memoria)
-- Experimento IT2iD (2026) - PostgreSQL JSONB
-- 
-- Objetivo: Filtrar órdenes completadas con timestamp >= 2026-01-01,
-- ordenar descendentemente por final_total y obtener Top-1000 sin índice en el total.
-- 
-- Variantes de estrés de memoria:
-- SET work_mem = '4MB';  -- Variante restrictiva (fuerza ordenamiento externo en disco)
-- SET work_mem = '64MB'; -- Variante holgada (permite ordenamiento en RAM)

SELECT 
    data->>'order_id' AS order_id,
    data->'customer'->>'id' AS customer_id,
    (data->'payment'->>'final_total')::numeric AS final_total
FROM 
    orders
WHERE 
    data->'payment'->>'status' = 'completed'
    AND (data->>'timestamp')::timestamptz >= '2026-01-01 00:00:00Z'
ORDER BY 
    (data->'payment'->>'final_total')::numeric DESC
LIMIT 1000;

