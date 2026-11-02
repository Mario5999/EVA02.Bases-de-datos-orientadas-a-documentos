# 07. Auditoría del Host y Entorno Docker

Este documento registra los resultados de la auditoría técnica realizada al sistema para certificar que cumple con todos los requisitos del experimento.

---

## 1. Especificaciones de Hardware y Sistema Operativo
* **Sistema Operativo:** Windows 10/11 (Kernel Microsoft WSL2 6.6.87.2)
* **Arquitectura:** x86_64
* **Espacio en Disco (C:\):** 63.55 GB libres de 474.72 GB totales (Aprobado ✅)

---

## 2. Entorno Docker y cgroups v2
* **Docker Client / Server:** Versión 29.1.3 (Aprobado ✅)
* **Docker Compose:** Versión v2.40.3 (Aprobado ✅)
* **Versión de cgroups:** **`Cgroup Version: 2`** (Exigido por la rúbrica) (Aprobado ✅)
* **Driver de cgroup:** `cgroupfs` (Aprobado ✅)
* **Storage Driver:** `overlayfs` con snapshotter `io.containerd.snapshotter.v1` (Aprobado ✅)
* **CPUs asignadas al motor Docker:** 8 CPUs (Requisito mínimo: 4 CPUs para Baseline) (Aprobado ✅)
* **Memoria RAM asignada al motor Docker:** 5.635 GiB (Requisito mínimo: 4.096 GiB para Baseline) (Aprobado ✅)
* **Límites efectivos tras recrear contenedores:** MongoDB y PostgreSQL usan 4 CPUs, 4096 MiB de memoria y `MemorySwap=4096 MiB` (`MemorySwappiness` no aplica en este entorno). cgroups v2 confirmado.

---

## 3. Entorno Python y Librerías de Benchmark
* **Versión:** Python 3.14.2
* **Entorno:** `venv/` aislado
* **Librerías verificadas con importación exitosa:**
  * `pymongo` (v4.19.0): Conector oficial MongoDB.
  * `psycopg2-binary` (v2.9.13): Conector oficial PostgreSQL.
  * `faker` (v40.44.0): Generador sintético.
  * `requests` (v2.34.2): Consulta de API HTTP de Prometheus.
  * `pandas` (v3.1.0): Análisis de matrices y CSV.
  * `numpy`: Percentiles estadísticos utilizados por el runner.
  * `matplotlib` (v3.11.2) y `seaborn` (v0.13.2): Gráficas estadísticas.

---

## 4. Auditoría de Red y Disponibilidad de Puertos
Se verificó que los puertos requeridos para los contenedores no presenten colisión con otros servicios locales:
* Puerto `27017` (MongoDB): **LIBRE ✅**
* Puerto `5433` (PostgreSQL, mapeado a 5432 del contenedor): **LIBRE ✅**
* Puerto `9090` (Prometheus): **LIBRE ✅**
* Puerto `8085` (cAdvisor, mapeado a 8080 del contenedor): **LIBRE ✅**
* Puerto `9100` (Node Exporter): **LIBRE ✅**

---

## 5. Dataset de Prueba
* **Archivo:** `dataset/orders_500k.jsonl`
* **Cantidad de registros:** 500,000 líneas; las 500,000 son JSON válidos.
* **Tamaño:** 573.58 MB.
* **Promedio de ítems:** 3.000852 (1,500,426 ítems totales; tolerancia ±0.01 cumplida).
* **Estado:** Dataset regenerado, validado y cargado en ambos motores; 500,000 registros por motor, promedio 3.0009 ítems, índices requeridos presentes.

## 6. Piloto del Runner y Telemetría
* **Escenario:** Q1, concurrencia 1, 30 segundos, perfil `PROFILE_A_BASELINE`.
* **MongoDB:** 13 consultas; 0.42 QPS; estado `SUCCESS`.
* **PostgreSQL:** 3 consultas; 0.09 QPS; estado `SUCCESS`.
* **CSV:** `mediciones_piloto_fase6.csv`, encabezado reglamentario y 14 columnas en ambas filas.
* **Alcance:** Este piloto valida el runner y el recolector en Q1; no constituye la matriz de benchmarks.
* **Q2_SORT_ALL:** piloto separado de cuatro combinaciones (dos motores × dos variantes), encabezado de 14 columnas y cuatro filas. MongoDB: sin disco `FAIL_MEMORY_LIMIT` y con disco `SUCCESS`/spill `True`; PostgreSQL: 4MB `SUCCESS`/spill `True` y 64MB `SUCCESS`/spill `False`.
* **Alcance:** Q2_SORT_ALL y las variantes alternativas son evidencia preparatoria, no parte de la matriz oficial del playbook.
* **Q2 Top-1000:** validación no oficial adicional, concurrencia 1, 2 s de warmup y 10 s de medición, perfil de contenedor actual. MongoDB: 12 consultas, 1.11 QPS, `SUCCESS`, spill `False`; PostgreSQL: 39 consultas, 3.81 QPS, `SUCCESS`, spill `False`. El CSV piloto independiente conserva el encabezado oficial de 14 columnas.
* **Matriz oficial:** 108 claves = 2 motores × 3 perfiles × 2 queries × 3 concurrencias × 3 repeticiones. La ejecución registró 99 claves `SUCCESS` y dejó 9 sin resultado válido, todas PostgreSQL Q1/concurrencia 50. PostgreSQL informó `No space left on device` al ampliar memoria compartida. Por decisión del usuario no se modificó `shm_size` ni se reintentaron las nueve claves.
* **Estado de análisis:** se generó un reporte parcial con medianas de ejecuciones exitosas, gráficos de latencia/throttling/RSS y comparación de planes. No presentar la matriz como completa. Fuentes: `mediciones.csv`, `mediciones_incidencias.log`, `matrix_resume_after_pg_shm.log` y `reporte_final_metricas.md`.
