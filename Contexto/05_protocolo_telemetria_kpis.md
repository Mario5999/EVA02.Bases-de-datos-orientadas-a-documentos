# 05. Protocolo de Ejecución, Telemetría y KPIs

## Protocolo de Ejecución
* **Niveles de Concurrencia:** 1, 10 y 50 clientes concurrentes.
* **Repeticiones:** 3 ejecuciones independientes por escenario para validez estadística.
* **Ciclo de Vida por Prueba:**
  1. *Flush de caché del host:* `sync; echo 3 >/proc/sys/vm/drop_caches`
  2. *Warmup (calentamiento):* 60 segundos.
  3. *Medición activa:* 300 segundos (5 minutos).
  4. *Cooldown (enfriamiento):* 60 segundos.
* **Matriz de Pruebas Total:**
  * 36 celdas: 2 motores × 3 perfiles de recursos × 2 queries (Q1 y Q2) × 3 niveles de concurrencia.
  * 3 repeticiones por celda: 36 × 3 = **108 corridas**.
  * Q2 utiliza una configuración fija por motor: MongoDB `allowDiskUse: false`; PostgreSQL `work_mem = '4MB'`. Las variantes alternativas de memoria no se duplican como escenarios.
  * Q2_SORT_ALL y cualquier escenario adicional quedan fuera de la matriz oficial, salvo aprobación posterior explícita.

---

## Stack de Telemetría
* **cAdvisor:** Monitoreo directo de métricas de contenedores (`cgroups v2`).
* **Node Exporter:** Monitoreo de host (I/O, disco, swap).
* **Prometheus:** Recolección de métricas con `scrape_interval: 1s`.

---

## Tabla de Indicadores Clave de Rendimiento (KPIs)

| KPI | Unidad | Tipo | Descripción |
| :--- | :---: | :--- | :--- |
| `throughput_qps` | queries/s | Performance | Consultas completadas por segundo |
| `latency_p50_ms` | ms | Performance | Tiempo de respuesta mediano |
| `latency_p95_ms` | ms | Performance | Percentil 95 de latencia |
| `latency_p99_ms` | ms | Performance | Percentil 99 de latencia (cola crítica) |
| `container_cpu_cfs_throttled_seconds_total` | s | OS / Contention | Segundos acumulados con CPU estrangulada |
| `container_memory_rss_bytes` | bytes | OS / Memory | Memoria RAM física ocupada |
| `disk_spill_detected` | boolean | Engine / Internal | PostgreSQL: incremento de `temp_bytes`; MongoDB: `usedDisk`/spills del explain con estadísticas de ejecución |
| `oom_killed` | boolean | Stability | Incremento de eventos OOM durante la corrida |

El RSS se toma como máximo de las muestras de Prometheus durante la ventana activa. Si Prometheus no responde o no devuelve una serie requerida, la corrida falla explícitamente; el recolector no convierte errores en ceros.

---

## Esquema CSV de Mediciones
El archivo final `mediciones.csv` conserva el encabezado obligatorio de 14 columnas. En la matriz oficial, `query_id` toma únicamente los valores `q1` y `q2`:
```csv
timestamp_epoch,engine,profile,query_id,concurrency,run_number,throughput_qps,latency_p50_ms,latency_p95_ms,latency_p99_ms,cpu_throttled_seconds,max_rss_mb,disk_spill,status
```
