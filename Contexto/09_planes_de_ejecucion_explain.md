# 09. Planes de Ejecución (Explain) - MongoDB vs PostgreSQL JSONB

Este documento contiene los planes de ejecución detallados requeridos por la **Sección 5** del reporte de métricas de la Universidad Politécnica de Chiapas.

---

## 1. Consulta Q1 (Unwind, Filter & Grouping - CPU Bound)

### 1.1. Plan de Ejecución en PostgreSQL: `EXPLAIN (ANALYZE, BUFFERS)`
```text
GroupAggregate  (cost=381080.71..3267845.83 rows=16499274 width=136) (actual time=1769.106..6899.736 rows=40 loops=1)
  Output: ((((orders.data -> 'customer'::text) -> 'geo'::text) ->> 'country'::text)), ((item.value ->> 'category'::text)), sum((((item.value ->> 'qty'::text))::numeric * ((item.value ->> 'price'::text))::numeric)), avg((((item.value ->> 'qty'::text))::numeric * ((item.value ->> 'price'::text))::numeric)), count(*)
  Group Key: ((((orders.data -> 'customer'::text) -> 'geo'::text) ->> 'country'::text)), ((item.value ->> 'category'::text))
  Buffers: shared hit=14550 read=84544, temp read=220386 written=220638
  ->  Incremental Sort  (cost=381080.71..2401633.95 rows=16499274 width=96) (actual time=1759.473..6243.317 rows=1251034 loops=1)
        Output: ((((orders.data -> 'customer'::text) -> 'geo'::text) ->> 'country'::text)), ((item.value ->> 'category'::text)), item.value
        Sort Key: ((((orders.data -> 'customer'::text) -> 'geo'::text) ->> 'country'::text)), ((item.value ->> 'category'::text))
        Presorted Key: ((((orders.data -> 'customer'::text) -> 'geo'::text) ->> 'country'::text))
        Full-sort Groups: 5  Sort Method: quicksort  Average Memory: 38kB  Peak Memory: 38kB
        Pre-sorted Groups: 5  Sort Method: external merge  Average Disk: 58956kB  Peak Disk: 98272kB
        Buffers: shared hit=14550 read=84544, temp read=220386 written=220638
        ->  Nested Loop  (cost=381077.10..1769249.26 rows=16499274 width=96) (actual time=1379.708..4133.657 rows=1251034 loops=1)
              Output: (((orders.data -> 'customer'::text) -> 'geo'::text) ->> 'country'::text), (item.value ->> 'category'::text), item.value
              Buffers: shared hit=14550 read=84544, temp read=177422 written=177603
              ->  Gather Merge  (cost=381077.10..439307.77 rows=499978 width=1437) (actual time=1377.862..2729.431 rows=500000 loops=1)
                    Output: orders.data
                    Workers Planned: 2
                    Workers Launched: 2
                    Buffers: shared hit=14550 read=84544, temp read=177422 written=177603
                    ->  Sort  (cost=380077.07..380597.88 rows=208324 width=1437) (actual time=1343.177..1573.924 rows=166667 loops=3)
                          Output: orders.data, ((((orders.data -> 'customer'::text) -> 'geo'::text) ->> 'country'::text))
                          Sort Key: ((((orders.data -> 'customer'::text) -> 'geo'::text) ->> 'country'::text))
                          Sort Method: external merge  Disk: 213152kB
                          Buffers: shared hit=14550 read=84544, temp read=177422 written=177603
                          Worker 0:  actual time=1344.471..1556.616 rows=174399 loops=1
                            Sort Method: external merge  Disk: 247496kB
                            JIT:
                              Functions: 2
                              Options: Inlining true, Optimization true, Expressions true, Deforming true
                              Timing: Generation 0.484 ms, Inlining 86.157 ms, Optimization 16.482 ms, Emission 12.107 ms, Total 115.230 ms
                            Buffers: shared hit=4824 read=29755, temp read=61872 written=61935
                          Worker 1:  actual time=1346.165..1678.289 rows=175439 loops=1
                            Sort Method: external merge  Disk: 249088kB
                            JIT:
                              Functions: 2
                              Options: Inlining true, Optimization true, Expressions true, Deforming true
                              Timing: Generation 0.858 ms, Inlining 77.092 ms, Optimization 15.469 ms, Emission 11.553 ms, Total 104.973 ms
                            Buffers: shared hit=4628 read=30159, temp read=62269 written=62333
                          ->  Parallel Seq Scan on public.orders  (cost=0.00..101063.24 rows=208324 width=1437) (actual time=159.776..337.441 rows=166667 loops=3)
                                Output: orders.data, (((orders.data -> 'customer'::text) -> 'geo'::text) ->> 'country'::text)
                                Buffers: shared hit=14436 read=84544
                                Worker 0:  actual time=114.861..296.221 rows=174399 loops=1
                                  Buffers: shared hit=4767 read=29755
                                Worker 1:  actual time=104.209..292.637 rows=175439 loops=1
                                  Buffers: shared hit=4571 read=30159
              ->  Function Scan on pg_catalog.jsonb_array_elements item  (cost=0.01..2.00 rows=33 width=32) (actual time=0.001..0.002 rows=3 loops=500000)
                    Output: item.value
                    Function Call: jsonb_array_elements((orders.data -> 'items'::text))
                    Filter: (((item.value ->> 'price'::text))::numeric > '50'::numeric)
                    Rows Removed by Filter: 0
Planning:
  Buffers: shared hit=194
Planning Time: 0.812 ms
JIT:
  Functions: 17
  Options: Inlining true, Optimization true, Expressions true, Deforming true
  Timing: Generation 2.296 ms, Inlining 271.212 ms, Optimization 114.933 ms, Emission 93.075 ms, Total 481.516 ms
Execution Time: 7024.282 ms
```

### 1.2. Plan de Ejecución en MongoDB: `explain('executionStats')`
* Etapas principales del pipeline: `$unwind`, `$match`, `$group`.
```json
[
  {
    "$cursor": {
      "queryPlanner": {
        "namespace": "benchmark_db.orders",
        "parsedQuery": {},
        "indexFilterSet": false,
        "queryHash": "51018CFF",
        "planCacheShapeHash": "51018CFF",
        "planCacheKey": "7CF6F44B",
        "optimizationTimeMillis": 0,
        "optimizationTimeMicros": 179,
        "cursorType": "regular",
        "maxIndexedOrSolutionsReached": false,
        "maxIndexedAndSolutionsReached": false,
        "maxScansToExplodeReached": false,
        "prunedSimilarIndexes": false,
        "winningPlan": {
          "isCached": false,
          "stage": "PROJECTION_DEFAULT",
          "transformBy": {
            "customer.geo.country": 1,
            "items": 1,
            "_id": 0
          },
          "inputStage": {
            "stage": "COLLSCAN",
            "nss": "benchmark_db.orders",
            "direction": "forward"
          }
        },
        "rejectedPlans": []
      },
      "executionStats": {
        "executionSuccess": true,
        "nReturned": 500000,
        "executionTimeMillis": 2571,
        "executionTimeMicros": 2571805,
        "totalKeysExamined": 0,
        "totalDocsExamined": 500000,
        "executionStages": {
          "isCached": false,
          "stage": "PROJECTION_DEFAULT",
          "nReturned": 500000,
          "executionTimeMillisEstimate": 205,
          "works": 500001,
          "advanced": 500000,
          "needTime": 0,
          "needYield": 0,
          "saveState": 144,
          "restoreState": 143,
          "isEOF": 1,
          "transformBy": {
            "customer.geo.country": 1,
            "items": 1,
            "_id": 0
          },
          "peakTrackedMemBytes": 0,
          "inputStage": {
            "stage": "COLLSCAN",
            "nReturned": 500000,
            "executionTimeMillisEstimate": 60,
            "works": 500001,
            "advanced": 500000,
            "needTime": 0,
            "needYield": 0,
            "saveState": 144,
            "restoreState": 143,
            "isEOF": 1,
            "nss": "benchmark_db.orders",
            "direction": "forward",
            "docsExamined": 500000,
            "seeks": 0
          }
        }
      }
    },
    "nReturned": 500000,
    "executionTimeMillisEstimate": 521
  },
  {
    "$unwind": {
      "path": "$items"
    },
    "nReturned": 1500426,
    "executionTimeMillisEstimate": 855
  },
  {
    "$match": {
      "items.price": {
        "$gt": 50
      }
    },
    "nReturned": 1251034,
    "executionTimeMillisEstimate": 1472,
    "expressionEvaluationPeakMemoryBytes": 512
  },
  {
    "$group": {
      "_id": {
        "country": "$customer.geo.country",
        "category": "$items.category"
      },
      "total_revenue": {
        "$sum": {
          "$multiply": [
            "$items.qty",
            "$items.price"
          ]
        }
      },
      "avg_revenue": {
        "$avg": {
          "$multiply": [
            "$items.qty",
       ... [truncado para legibilidad]
```

---

## 2. Consulta Q2 (Massive Sort & Top-K - Memory Buffer Bound)

### 2.1. PostgreSQL con `work_mem = '4MB'` (Volcado a disco / External Merge)
```text
Limit  (cost=105729.65..105810.62 rows=694 width=96) (actual time=288.410..298.230 rows=1000 loops=1)
  Output: ((data ->> 'order_id'::text)), (((data -> 'customer'::text) ->> 'id'::text)), ((((data -> 'payment'::text) ->> 'final_total'::text))::numeric)
  Buffers: shared hit=14644 read=84448
  ->  Gather Merge  (cost=105729.65..105810.62 rows=694 width=96) (actual time=285.234..294.955 rows=1000 loops=1)
        Output: ((data ->> 'order_id'::text)), (((data -> 'customer'::text) ->> 'id'::text)), ((((data -> 'payment'::text) ->> 'final_total'::text))::numeric)
        Workers Planned: 2
        Workers Launched: 2
        Buffers: shared hit=14644 read=84448
        ->  Sort  (cost=104729.63..104730.50 rows=347 width=96) (actual time=264.586..264.679 rows=797 loops=3)
              Output: ((data ->> 'order_id'::text)), (((data -> 'customer'::text) ->> 'id'::text)), ((((data -> 'payment'::text) ->> 'final_total'::text))::numeric)
              Sort Key: ((((orders.data -> 'payment'::text) ->> 'final_total'::text))::numeric) DESC
              Sort Method: top-N heapsort  Memory: 273kB
              Buffers: shared hit=14644 read=84448
              Worker 0:  actual time=254.641..254.753 rows=1000 loops=1
                Sort Method: top-N heapsort  Memory: 275kB
                JIT:
                  Functions: 4
                  Options: Inlining false, Optimization false, Expressions true, Deforming true
                  Timing: Generation 0.485 ms, Inlining 0.000 ms, Optimization 0.322 ms, Emission 5.550 ms, Total 6.357 ms
                Buffers: shared hit=4524 read=26589
              Worker 1:  actual time=254.748..254.860 rows=1000 loops=1
                Sort Method: top-N heapsort  Memory: 272kB
                JIT:
                  Functions: 4
                  Options: Inlining false, Optimization false, Expressions true, Deforming true
                  Timing: Generation 0.805 ms, Inlining 0.000 ms, Optimization 0.346 ms, Emission 4.318 ms, Total 5.469 ms
                Buffers: shared hit=4465 read=26664
              ->  Parallel Seq Scan on public.orders  (cost=0.00..104714.99 rows=347 width=96) (actual time=3.598..238.197 rows=65034 loops=3)
                    Output: (data ->> 'order_id'::text), ((data -> 'customer'::text) ->> 'id'::text), (((data -> 'payment'::text) ->> 'final_total'::text))::numeric
                    Filter: ((((orders.data -> 'payment'::text) ->> 'status'::text) = 'completed'::text) AND (((orders.data ->> 'timestamp'::text))::timestamp with time zone >= '2026-01-01 00:00:00+00'::timestamp with time zone))
                    Rows Removed by Filter: 101633
                    Buffers: shared hit=14532 read=84448
                    Worker 0:  actual time=5.952..229.446 rows=61007 loops=1
                      Buffers: shared hit=4468 read=26589
                    Worker 1:  actual time=4.763..229.865 rows=61170 loops=1
                      Buffers: shared hit=4409 read=26664
Planning:
  Buffers: shared hit=13
Planning Time: 0.095 ms
JIT:
  Functions: 13
  Options: Inlining false, Optimization false, Expressions true, Deforming true
  Timing: Generation 1.855 ms, Inlining 0.000 ms, Optimization 0.843 ms, Emission 12.873 ms, Total 15.572 ms
Execution Time: 298.981 ms
```

### 2.2. PostgreSQL con `work_mem = '64MB'` (Ordenamiento en Memoria / Quicksort)
```text
Limit  (cost=105729.65..105810.62 rows=694 width=96) (actual time=310.896..319.797 rows=1000 loops=1)
  Output: ((data ->> 'order_id'::text)), (((data -> 'customer'::text) ->> 'id'::text)), ((((data -> 'payment'::text) ->> 'final_total'::text))::numeric)
  Buffers: shared hit=14740 read=84352
  ->  Gather Merge  (cost=105729.65..105810.62 rows=694 width=96) (actual time=308.297..317.140 rows=1000 loops=1)
        Output: ((data ->> 'order_id'::text)), (((data -> 'customer'::text) ->> 'id'::text)), ((((data -> 'payment'::text) ->> 'final_total'::text))::numeric)
        Workers Planned: 2
        Workers Launched: 2
        Buffers: shared hit=14740 read=84352
        ->  Sort  (cost=104729.63..104730.50 rows=347 width=96) (actual time=288.387..288.505 rows=786 loops=3)
              Output: ((data ->> 'order_id'::text)), (((data -> 'customer'::text) ->> 'id'::text)), ((((data -> 'payment'::text) ->> 'final_total'::text))::numeric)
              Sort Key: ((((orders.data -> 'payment'::text) ->> 'final_total'::text))::numeric) DESC
              Sort Method: top-N heapsort  Memory: 273kB
              Buffers: shared hit=14740 read=84352
              Worker 0:  actual time=278.613..278.744 rows=1000 loops=1
                Sort Method: top-N heapsort  Memory: 273kB
                JIT:
                  Functions: 4
                  Options: Inlining false, Optimization false, Expressions true, Deforming true
                  Timing: Generation 0.972 ms, Inlining 0.000 ms, Optimization 0.265 ms, Emission 4.326 ms, Total 5.564 ms
                Buffers: shared hit=4681 read=26791
              Worker 1:  actual time=278.621..278.789 rows=1000 loops=1
                Sort Method: top-N heapsort  Memory: 270kB
                JIT:
                  Functions: 4
                  Options: Inlining false, Optimization false, Expressions true, Deforming true
                  Timing: Generation 0.751 ms, Inlining 0.000 ms, Optimization 0.254 ms, Emission 5.340 ms, Total 6.346 ms
                Buffers: shared hit=4568 read=26991
              ->  Parallel Seq Scan on public.orders  (cost=0.00..104714.99 rows=347 width=96) (actual time=3.479..259.459 rows=65034 loops=3)
                    Output: (data ->> 'order_id'::text), ((data -> 'customer'::text) ->> 'id'::text), (((data -> 'payment'::text) ->> 'final_total'::text))::numeric
                    Filter: ((((orders.data -> 'payment'::text) ->> 'status'::text) = 'completed'::text) AND (((orders.data ->> 'timestamp'::text))::timestamp with time zone >= '2026-01-01 00:00:00+00'::timestamp with time zone))
                    Rows Removed by Filter: 101633
                    Buffers: shared hit=14628 read=84352
                    Worker 0:  actual time=4.691..249.139 rows=61984 loops=1
                      Buffers: shared hit=4625 read=26791
                    Worker 1:  actual time=5.706..250.389 rows=61988 loops=1
                      Buffers: shared hit=4512 read=26991
Planning Time: 0.082 ms
JIT:
  Functions: 13
  Options: Inlining false, Optimization false, Expressions true, Deforming true
  Timing: Generation 2.069 ms, Inlining 0.000 ms, Optimization 0.703 ms, Emission 12.088 ms, Total 14.859 ms
Execution Time: 320.268 ms
```

### 2.3. MongoDB Q2 `explain('executionStats')`
```json
{
  "explainVersion": "1",
  "queryPlanner": {
    "namespace": "benchmark_db.orders",
    "parsedQuery": {
      "$and": [
        {
          "payment.status": {
            "$eq": "completed"
          }
        },
        {
          "timestamp": {
            "$gte": "2026-01-01T00:00:00Z"
          }
        }
      ]
    },
    "indexFilterSet": false,
    "queryHash": "1F1F8489",
    "planCacheShapeHash": "1F1F8489",
    "planCacheKey": "57042284",
    "optimizationTimeMillis": 0,
    "optimizationTimeMicros": 230,
    "optimizedPipeline": true,
    "maxIndexedOrSolutionsReached": false,
    "maxIndexedAndSolutionsReached": false,
    "maxScansToExplodeReached": false,
    "prunedSimilarIndexes": false,
    "winningPlan": {
      "isCached": false,
      "stage": "PROJECTION_DEFAULT",
      "transformBy": {
        "_id": true,
        "order_id": true,
        "customer": {
          "id": true
        },
        "payment": {
          "final_total": true
        }
      },
      "inputStage": {
        "stage": "SORT",
        "sortPattern": {
          "payment.final_total": -1
        },
        "memLimit": 104857600,
        "limitAmount": 1000,
        "type": "simple",
        "inputStage": {
          "stage": "FETCH",
          "filter": {
            "payment.status": {
              "$eq": "completed"
            }
          },
          "nss": "benchmark_db.orders",
          "inputStage": {
            "stage": "IXSCAN",
            "nss": "benchmark_db.orders",
            "keyPattern": {
              "timestamp": 1
            },
            "indexName": "idx_timestamp",
            "isMultiKey": false,
            "multiKeyPaths": {
              "timestamp": []
            },
            "isUnique": false,
            "isSparse": false,
            "isPartial": false,
            "indexVersion": 2,
            "direction": "forward",
            "indexBounds": {
              "timestamp": [
                "[\"2026-01-01T00:00:00Z\", {})"
              ]
            }
          }
        }
      }
    },
    "rejectedPlans": []
  },
  "executionStats": {
    "executionSuccess": true,
    "nReturned": 1000,
    "executionTimeMillis": 903,
    "executionTimeMicros": 903088,
    "totalKeysExamined": 293342,
    "totalDocsExamined": 293342,
    "executionStages": {
      "isCached": false,
      "stage": "PROJECTION_DEFAULT",
      "nReturned": 1000,
      "executionTimeMillisEstimate": 899,
      "works": 294344,
      "advanced": 1000,
      "needTime": 293343,
      "needYield": 0,
      "saveState": 45,
      "restoreState": 45,
      "isEOF": 1,
      "transformBy": {
        "_id": true,
        "order_id": true,
        "customer": {
          "id": true
        },
        "payment": {
          "final_total": true
        }
      },
      "peakTrackedMemBytes": 0,
      "inputStage": {
        "stage": "SORT",
        "nReturned": 1000,
        "executionTimeMillisEstimate": 899,
        "works": 294344,
        "adv ... [truncado para legibilidad]
```

---

## 3. Q2_SORT_ALL (ordenación completa)

Esta consulta auxiliar se documenta como evidencia de EXPLAIN/pilotos preparatorios. No forma parte de la matriz oficial de 108 corridas definida en la sección 6 del playbook. No ejecutarla en la matriz salvo aprobación posterior explícita.

### 3.1. PostgreSQL con `work_mem = '4MB'`
```text
Aggregate  (cost=112811.46..112811.47 rows=1 width=48) (actual time=742.085..742.087 rows=1 loops=1)
  Output: count(*), max((row_number() OVER (?))), sum((((row_number() OVER (?)))::numeric * ((((orders.data -> 'payment'::text) ->> 'final_total'::text))::numeric)))
  Buffers: shared hit=14724 read=84256, temp read=335 written=337
  ->  WindowAgg  (cost=112778.13..112801.04 rows=833 width=40) (actual time=639.704..702.164 rows=195101 loops=1)
        Output: row_number() OVER (?), ((((orders.data -> 'payment'::text) ->> 'final_total'::text))::numeric)
        Buffers: shared hit=14724 read=84256, temp read=335 written=337
        ->  Sort  (cost=112778.13..112780.22 rows=833 width=32) (actual time=639.663..662.006 rows=195101 loops=1)
              Output: ((((orders.data -> 'payment'::text) ->> 'final_total'::text))::numeric)
              Sort Key: ((((orders.data -> 'payment'::text) ->> 'final_total'::text))::numeric) DESC
              Sort Method: external merge  Disk: 2680kB
              Buffers: shared hit=14724 read=84256, temp read=335 written=337
              ->  Seq Scan on public.orders  (cost=0.00..112737.73 rows=833 width=32) (actual time=6.738..556.568 rows=195101 loops=1)
                    Output: (((orders.data -> 'payment'::text) ->> 'final_total'::text))::numeric
                    Filter: ((((orders.data -> 'payment'::text) ->> 'status'::text) = 'completed'::text) AND (((orders.data ->> 'timestamp'::text))::timestamp with time zone >= '2026-01-01 00:00:00+00'::timestamp with time zone))
                    Rows Removed by Filter: 304899
                    Buffers: shared hit=14724 read=84256
Planning:
  Buffers: shared hit=3
Planning Time: 0.098 ms
JIT:
  Functions: 9
  Options: Inlining false, Optimization false, Expressions true, Deforming true
  Timing: Generation 0.692 ms, Inlining 0.000 ms, Optimization 0.302 ms, Emission 6.439 ms, Total 7.434 ms
Execution Time: 744.371 ms
```

### 3.2. PostgreSQL con `work_mem = '64MB'`
```text
Aggregate  (cost=112811.46..112811.47 rows=1 width=48) (actual time=802.246..802.248 rows=1 loops=1)
  Output: count(*), max((row_number() OVER (?))), sum((((row_number() OVER (?)))::numeric * ((((orders.data -> 'payment'::text) ->> 'final_total'::text))::numeric)))
  Buffers: shared hit=14756 read=84224
  ->  WindowAgg  (cost=112778.13..112801.04 rows=833 width=40) (actual time=684.864..760.429 rows=195101 loops=1)
        Output: row_number() OVER (?), ((((orders.data -> 'payment'::text) ->> 'final_total'::text))::numeric)
        Buffers: shared hit=14756 read=84224
        ->  Sort  (cost=112778.13..112780.22 rows=833 width=32) (actual time=684.812..692.921 rows=195101 loops=1)
              Output: ((((orders.data -> 'payment'::text) ->> 'final_total'::text))::numeric)
              Sort Key: ((((orders.data -> 'payment'::text) ->> 'final_total'::text))::numeric) DESC
              Sort Method: quicksort  Memory: 10702kB
              Buffers: shared hit=14756 read=84224
              ->  Seq Scan on public.orders  (cost=0.00..112737.73 rows=833 width=32) (actual time=5.215..596.178 rows=195101 loops=1)
                    Output: (((orders.data -> 'payment'::text) ->> 'final_total'::text))::numeric
                    Filter: ((((orders.data -> 'payment'::text) ->> 'status'::text) = 'completed'::text) AND (((orders.data ->> 'timestamp'::text))::timestamp with time zone >= '2026-01-01 00:00:00+00'::timestamp with time zone))
                    Rows Removed by Filter: 304899
                    Buffers: shared hit=14756 read=84224
Planning Time: 0.092 ms
JIT:
  Functions: 9
  Options: Inlining false, Optimization false, Expressions true, Deforming true
  Timing: Generation 0.632 ms, Inlining 0.000 ms, Optimization 0.226 ms, Emission 4.982 ms, Total 5.840 ms
Execution Time: 803.957 ms
```

### 3.3. MongoDB con `allowDiskUse: false`
* Indicadores de ejecución: `{"executionFailure": "Sort exceeded memory limit of 104857600 bytes, but did not opt in to external sorting., full error: {'ok': 0.0, 'errmsg': 'Sort exceeded memory limit of 104857600 bytes, but did not opt in to external sorting.', 'code': 292, 'codeName': 'QueryExceededMemoryLimitNoDiskUseAllowed'}"}`
```json
{
  "executionFailure": "Sort exceeded memory limit of 104857600 bytes, but did not opt in to external sorting., full error: {'ok': 0.0, 'errmsg': 'Sort exceeded memory limit of 104857600 bytes, but did not opt in to external sorting.', 'code': 292, 'codeName': 'QueryExceededMemoryLimitNoDiskUseAllowed'}"
} ... [truncado para legibilidad]
```

### 3.4. MongoDB con `allowDiskUse: true`
* Indicadores de ejecución: `{"executionSuccess": null, "executionTimeMillis": null, "nReturned": null, "spillIndicators": [{"usedDisk": true, "spills": 3}, {"usedDisk": false, "spills": 0}, {"usedDisk": false, "spills": 0}]}`
```json
[
  {
    "$cursor": {
      "queryPlanner": {
        "namespace": "benchmark_db.orders",
        "parsedQuery": {
          "$and": [
            {
              "payment.status": {
                "$eq": "completed"
              }
            },
            {
              "timestamp": {
                "$gte": "2026-01-01T00:00:00Z"
              }
            }
          ]
        },
        "indexFilterSet": false,
        "queryHash": "DBB98C84",
        "planCacheShapeHash": "DBB98C84",
        "planCacheKey": "401D1FAB",
        "optimizationTimeMillis": 0,
        "optimizationTimeMicros": 128,
        "cursorType": "regular",
        "maxIndexedOrSolutionsReached": false,
        "maxIndexedAndSolutionsReached": false,
        "maxScansToExplodeReached": false,
        "prunedSimilarIndexes": false,
        "winningPlan": {
          "isCached": false,
          "stage": "SORT",
          "sortPattern": {
            "payment.final_total": -1
          },
          "memLimit": 104857600,
          "type": "simple",
          "inputStage": {
            "stage": "FETCH",
            "filter": {
              "payment.status": {
                "$eq": "completed"
              }
            },
            "nss": "benchmark_db.orders",
            "inputStage": {
              "stage": "IXSCAN",
              "nss": "benchmark_db.orders",
              "keyPattern": {
                "timestamp": 1
              },
              "indexName": "idx_timestamp",
              "isMultiKey": false,
              "multiKeyPaths": {
                "timestamp": []
              },
              "isUnique": false,
              "isSparse": false,
              "isPartial": false,
              "indexVersion": 2,
              "direction": "forward",
              "indexBounds": {
                "timestamp": [
                  "[\"2026-01-01T00:00:00Z\", {})"
                ]
              }
            }
          }
        },
        "rejectedPlans": []
      },
      "executionStats": {
        "executionSuccess": true,
        "nReturned": 195101,
        "executionTimeMillis": 2110,
        "executionTimeMicros": 2110228,
        "totalKeysExamined": 293342,
        "totalDocsExamined": 293342,
        "executionStages": {
          "isCached": false,
          "stage": "SORT",
          "nReturned": 195101,
          "executionTimeMillisEstimate": 1658,
          "works": 488445,
          "advanced": 195101,
          "needTime": 293343,
          "needYield": 0,
          "saveState": 138,
          "restoreState": 137,
          "isEOF": 1,
          "sortPattern": {
            "payment.final_total": -1
          },
          "memLimit": 104857600,
          "type": "simple",
          "totalDataSizeSorted": 237872434,
          "usedDisk": true,
          "spills": 3,
          "spilledRecords": 195101,
          "spilledBytes": 233385111,
          "spilledDataStorageSize": 65054982,
          "peakTrackedMemBytes": 103809092,
      ... [truncado para legibilidad]
```
