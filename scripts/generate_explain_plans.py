#!/usr/bin/env python3
"""
Generador y extractor de Planes de Ejecución (Explain)
Experimento IT2iD (2026)
Extrae explain('executionStats') de MongoDB y EXPLAIN (ANALYZE, BUFFERS) de PostgreSQL.
Genera el archivo Contexto/09_planes_de_ejecucion_explain.md para el reporte final.
"""

import os
import sys
import json
import time
import pymongo
from pymongo.errors import OperationFailure
from bson import json_util
import psycopg2

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUTPUT_MD = os.path.join("Contexto", "09_planes_de_ejecucion_explain.md")

def explain_mongo(db, pipeline, allow_disk_use):
    command = {
        "aggregate": "orders",
        "pipeline": pipeline,
        "cursor": {},
        "allowDiskUse": allow_disk_use
    }
    try:
        return db.command({
            "explain": command,
            "verbosity": "executionStats"
        })
    except OperationFailure as exc:
        if exc.code == 292:
            return {"executionFailure": str(exc)}
        raise

def mongo_execution_summary(explain):
    if "executionFailure" in explain:
        return {"executionFailure": explain["executionFailure"]}

    stats = explain.get("executionStats", {})
    indicators = []

    def collect(value):
        if isinstance(value, dict):
            if "usedDisk" in value or "spills" in value:
                indicators.append({
                    key: value[key]
                    for key in ("usedDisk", "spills")
                    if key in value
                })
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(explain)
    return {
        "executionSuccess": stats.get("executionSuccess"),
        "executionTimeMillis": stats.get("executionTimeMillis"),
        "nReturned": stats.get("nReturned"),
        "spillIndicators": indicators,
    }

def main():
    print("==================================================")
    print("[*] Obteniendo Planes de Ejecucion (Explain)...")
    print("==================================================")

    # 1. MongoDB Connect
    mc = pymongo.MongoClient("mongodb://localhost:27017/")
    m_db = mc["benchmark_db"]
    m_coll = m_db["orders"]

    # Mongo Q1 Pipeline
    q1_pipeline = [
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

    print("[*] Ejecutando explain('executionStats') en MongoDB para Q1...")
    m_q1_explain = explain_mongo(m_db, q1_pipeline, True)

    # Mongo Q2 Pipeline
    q2_pipeline = [
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

    print("[*] Ejecutando explain('executionStats') en MongoDB para Q2...")
    m_q2_explain = explain_mongo(m_db, q2_pipeline, False)

    q2_sort_all_pipeline = [
        { "$match": {
            "payment.status": "completed",
            "timestamp": { "$gte": "2026-01-01T00:00:00Z" }
        } },
        { "$setWindowFields": {
            "sortBy": { "payment.final_total": -1 },
            "output": { "rank": { "$documentNumber": {} } }
        } },
        { "$group": {
            "_id": None,
            "count": { "$sum": 1 },
            "rank_sum": { "$sum": "$rank" },
            "highest_total": { "$max": "$payment.final_total" },
            "lowest_total": { "$min": "$payment.final_total" }
        } }
    ]
    print("[*] Ejecutando explain de Q2_SORT_ALL para ambas variantes MongoDB...")
    m_q2_sort_all_low_explain = explain_mongo(m_db, q2_sort_all_pipeline, False)
    m_q2_sort_all_high_explain = explain_mongo(m_db, q2_sort_all_pipeline, True)

    # 2. PostgreSQL Connect
    pg = psycopg2.connect(
        host="localhost", port=5433, user="benchmark", password="benchmark", dbname="benchmark_db"
    )
    pg.autocommit = True
    cur = pg.cursor()

    # Postgres Q1
    pg_q1_sql = """
    EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT)
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
    """
    print("[*] Ejecutando EXPLAIN (ANALYZE, BUFFERS) en PostgreSQL para Q1...")
    cur.execute(pg_q1_sql)
    pg_q1_explain = "\n".join(row[0] for row in cur.fetchall())

    # Postgres Q2 (work_mem = '4MB')
    print("[*] Ejecutando EXPLAIN en PostgreSQL para Q2 con work_mem = '4MB'...")
    cur.execute("SET work_mem = '4MB';")
    pg_q2_sql = """
    EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT)
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
    """
    cur.execute(pg_q2_sql)
    pg_q2_4mb_explain = "\n".join(row[0] for row in cur.fetchall())

    # Postgres Q2 (work_mem = '64MB')
    print("[*] Ejecutando EXPLAIN en PostgreSQL para Q2 con work_mem = '64MB'...")
    cur.execute("SET work_mem = '64MB';")
    cur.execute(pg_q2_sql)
    pg_q2_64mb_explain = "\n".join(row[0] for row in cur.fetchall())

    pg_q2_sort_all_sql = """
    EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT)
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
    """
    print("[*] Ejecutando EXPLAIN de Q2_SORT_ALL con work_mem = '4MB'...")
    cur.execute("SELECT set_config('work_mem', '4MB', false);")
    cur.execute("SET max_parallel_workers_per_gather = 0;")
    cur.execute(pg_q2_sort_all_sql)
    pg_q2_sort_all_4mb_explain = "\n".join(row[0] for row in cur.fetchall())

    print("[*] Ejecutando EXPLAIN de Q2_SORT_ALL con work_mem = '64MB'...")
    cur.execute("SELECT set_config('work_mem', '64MB', false);")
    cur.execute("SET max_parallel_workers_per_gather = 0;")
    cur.execute(pg_q2_sort_all_sql)
    pg_q2_sort_all_64mb_explain = "\n".join(row[0] for row in cur.fetchall())

    cur.close()
    pg.close()

    # 3. Guardar documento en Markdown
    print(f"[*] Guardando resultados en {OUTPUT_MD}...")
    contenido_md = f"""# 09. Planes de Ejecución (Explain) - MongoDB vs PostgreSQL JSONB

Este documento contiene los planes de ejecución detallados requeridos por la **Sección 5** del reporte de métricas de la Universidad Politécnica de Chiapas.

---

## 1. Consulta Q1 (Unwind, Filter & Grouping - CPU Bound)

### 1.1. Plan de Ejecución en PostgreSQL: `EXPLAIN (ANALYZE, BUFFERS)`
```text
{pg_q1_explain}
```

### 1.2. Plan de Ejecución en MongoDB: `explain('executionStats')`
* Etapas principales del pipeline: `$unwind`, `$match`, `$group`.
```json
{json_util.dumps(m_q1_explain.get('stages', m_q1_explain), indent=2)[:3000]} ... [truncado para legibilidad]
```

---

## 2. Consulta Q2 (Massive Sort & Top-K - Memory Buffer Bound)

### 2.1. PostgreSQL con `work_mem = '4MB'` (Volcado a disco / External Merge)
```text
{pg_q2_4mb_explain}
```

### 2.2. PostgreSQL con `work_mem = '64MB'` (Ordenamiento en Memoria / Quicksort)
```text
{pg_q2_64mb_explain}
```

### 2.3. MongoDB Q2 `explain('executionStats')`
```json
{json_util.dumps(m_q2_explain.get('stages', m_q2_explain), indent=2)[:3000]} ... [truncado para legibilidad]
```

---

## 3. Q2_SORT_ALL (ordenación completa)

### 3.1. PostgreSQL con `work_mem = '4MB'`
```text
{pg_q2_sort_all_4mb_explain}
```

### 3.2. PostgreSQL con `work_mem = '64MB'`
```text
{pg_q2_sort_all_64mb_explain}
```

### 3.3. MongoDB con `allowDiskUse: false`
* Indicadores de ejecución: `{json_util.dumps(mongo_execution_summary(m_q2_sort_all_low_explain))}`
```json
{json_util.dumps(m_q2_sort_all_low_explain.get('stages', m_q2_sort_all_low_explain), indent=2)[:3000]} ... [truncado para legibilidad]
```

### 3.4. MongoDB con `allowDiskUse: true`
* Indicadores de ejecución: `{json_util.dumps(mongo_execution_summary(m_q2_sort_all_high_explain))}`
```json
{json_util.dumps(m_q2_sort_all_high_explain.get('stages', m_q2_sort_all_high_explain), indent=2)[:3000]} ... [truncado para legibilidad]
```
"""

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(contenido_md)

    print("\n[+] Planes de ejecucion generados y guardados con exito en:")
    print(f"    {OUTPUT_MD}\n")

if __name__ == "__main__":
    main()
