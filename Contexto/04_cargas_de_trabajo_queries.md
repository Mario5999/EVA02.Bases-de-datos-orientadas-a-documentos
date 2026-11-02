# 04. Cargas de Trabajo (Consultas Q1 y Q2)

## 1. Q1 — Unwind, Filter & Grouping (Saturación de CPU)
* **Objetivo:** Desanidar el arreglo de ítems, filtrar `price > 50`, calcular subtotal (`qty * price`) y agrupar sumatoria y promedio de ingresos por país y categoría.

### MongoDB Pipeline:
```javascript
[
  { "$unwind": "$items" },
  { "$match": { "items.price": { "$gt": 50 } } },
  {
    "$group": {
      "_id": {
        "country": "$customer.geo.country",
        "category": "$items.category"
      },
      "total_revenue": { "$sum": { "$multiply": ["$items.qty", "$items.price"] } },
      "avg_revenue": { "$avg": { "$multiply": ["$items.qty", "$items.price"] } },
      "count": { "$sum": 1 }
    }
  }
]
```

### PostgreSQL JSONB Query:
```sql
SELECT data->'customer'->'geo'->>'country' AS country,
       item->>'category' AS category,
       SUM((item->>'qty')::numeric * (item->>'price')::numeric) AS total_revenue,
       AVG((item->>'qty')::numeric * (item->>'price')::numeric) AS avg_revenue,
       COUNT(*) AS count
FROM orders, jsonb_array_elements(data->'items') AS item
WHERE (item->>'price')::numeric > 50
GROUP BY 1, 2;
```

---

## 2. Q2 — Massive Sort & Top-K (Estrés de Buffer de Memoria)
* **Objetivo:** Filtrar órdenes completadas con `timestamp >= '2026-01-01T00:00:00Z'`, ordenar descendentemente por `payment.final_total` y obtener el Top-1000 sin índices en el total.

### Variantes de Estrés de Memoria:
* **MongoDB:**
  * `allowDiskUse: false` (debe fallar si excede 100MB RAM de buffer de ordenamiento).
  * `allowDiskUse: true` (se permite volcado a disco).
* **PostgreSQL:**
  * `SET work_mem = '4MB'` (fuerza volcado a disco temporal externo).
  * `SET work_mem = '64MB'` (intenta ordenar en memoria).
* **Configuración fija de la matriz oficial (sección 6 del playbook):** MongoDB usa `allowDiskUse: false` y PostgreSQL usa `work_mem = '4MB'`. Las variantes `true` y `64MB` no son factores adicionales de la matriz de 108 corridas.

### MongoDB Pipeline:
```javascript
[
  { "$match": {
      "payment.status": "completed",
      "timestamp": { "$gte": "2026-01-01T00:00:00Z" }
  } },
  { "$sort": { "payment.final_total": -1 } },
  { "$limit": 1000 },
  { "$project": {
      "order_id": 1, "customer.id": 1, "payment.final_total": 1
  } }
]
```

### Q2_SORT_ALL — Variante independiente para observar spill de memoria

El Top-1000 original se conserva como Q2 y no se presume que desborde memoria: el motor puede optimizarlo como Top-N. Para medir ordenación completa se agregó una carga separada que ordena todas las órdenes que cumplen los filtros y después resume el resultado. Esta carga y sus variantes se usaron solo en EXPLAIN/pilotos preparatorios: están fuera de la matriz oficial de 108 corridas y no se ejecutarán como parte de ella sin aprobación posterior.

* **MongoDB:** `queries/mongo_q2_sort_all.js`, variantes `allowDiskUse: false` y `true`.
* **PostgreSQL:** `queries/postgres_q2_sort_all.sql`, variantes `work_mem = 4MB` y `64MB`; el runner desactiva paralelismo solo para esta carga, y la ventana `ROW_NUMBER()` fuerza a completar el ordenamiento.
* `disk_spill` se registra a partir de evidencia del motor, no por el nombre de la variante.

### PostgreSQL JSONB Query:
```sql
SELECT data->>'order_id' AS order_id,
       data->'customer'->>'id' AS customer_id,
       (data->'payment'->>'final_total')::numeric AS final_total
FROM orders
WHERE data->'payment'->>'status' = 'completed'
  AND (data->>'timestamp')::timestamptz >= '2026-01-01 00:00:00Z'
ORDER BY (data->'payment'->>'final_total')::numeric DESC
LIMIT 1000;
```
