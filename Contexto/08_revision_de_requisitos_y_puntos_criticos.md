# 08. Revisión Exhaustiva de Requisitos y Puntos Críticos

Este documento consolida la auditoría profunda de todos los requisitos del experimento solicitados por la Universidad Politécnica de Chiapas, asegurando que **ningún detalle técnico se pase por alto o se dé por sentado**.

---

## 1. Auditoría Matemática y de Integridad del Dataset
Se ejecutó un script de verificación sobre los 500,000 registros generados en `dataset/orders_500k.jsonl`:

* **Total de líneas analizadas:** 500,000 registros.
* **Integridad estructural (JSON válido con todos los campos clave):** 500,000 (100.0% éxito).
* **Distribución para Q1 (Saturación de CPU):**
  * Total de ítems anidados generados: ~1.5 millones.
  * Ítems con `price > 50`: **1,167,282 ítems**.  
  * *Veredicto:* Garantiza una carga de cómputo pesada para el CPU al desarmar arreglos y calcular sumatorias y promedios.
* **Distribución para Q2 (Estrés de Buffer de Memoria):**
  * Registros con `payment.status == 'completed'`: **333,084 órdenes (66.6%)**.
  * Registros con `timestamp >= '2026-01-01'`: **293,292 órdenes (58.7%)**.
  * *Veredicto:* Existen más de 190,000 órdenes que cumplen ambos criterios simultáneamente, obligando al motor a ordenar un volumen masivo en RAM para obtener el Top 1000.

---

## 2. Puntos Críticos de Infraestructura y Soluciones

### Punto Crítico A: Flush de Caché (`drop_caches`) en Windows/WSL2
* **Exigencia del documento:** Ejecutar `sync; echo 3 >/proc/sys/vm/drop_caches` antes de cada corrida para purgar la caché de disco de la memoria RAM del sistema operativo.
* **Desafío técnico en Windows:** PowerShell en Windows no tiene una ruta `/proc/sys/vm/drop_caches` nativa porque es un kernel NT, mientras que Docker corre en una máquina virtual Linux ligera (WSL2).
* **Solución técnica implementada:** Disparar la orden mediante un contenedor Alpine temporal privilegiado:
  ```bash
  docker run --rm --privileged alpine sh -c "sync; echo 3 > /proc/sys/vm/drop_caches"
  ```
  Esto purga la memoria caché directamente en el kernel Linux donde residen los contenedores de las bases de datos.

### Punto Crítico B: Control Estricto de Recursos (`cgroups v2` y swap)
* **Exigencia del documento:**
  * Perfil A: 4.0 CPU, 4096 MB RAM.
  * Perfil B: 2.0 CPU, 2048 MB RAM.
  * Perfil C: 1.0 CPU, 1024 MB RAM (throttling activo).
  * Swap deshabilitado en los tres perfiles.
* **Verificación:** Docker Desktop opera con **`Cgroup Version: 2`** y tiene asignados 8 CPUs y aproximadamente 5.6 GB RAM. El Compose limita `memswap_limit` al mismo valor que `memory`, evitando swap del contenedor. `mem_swappiness` por sí solo no se toma como evidencia; se debe inspeccionar la configuración efectiva del contenedor en el entorno de ejecución.

### Punto Crítico E: Promedio de ítems y consistencia del dataset
* La distribución anterior del generador tenía promedio esperado de **2.8 ítems**, no 3.
* El generador ahora usa una distribución con promedio esperado de 3, y la auditoría verifica el promedio en ambas bases.
* **Antes de benchmarks:** regenerar `dataset/orders_500k.jsonl` y recargar MongoDB y PostgreSQL. La auditoría inicial del orquestador detendrá la ejecución si las bases actuales no cumplen el promedio.

### Punto Crítico C: Prevención de Descargas Durante las Mediciones
* Para evitar que la descarga de imágenes Docker altere las mediciones de latencia, CPU o red durante los benchmarks, se realizará una **pre-descarga (pre-pull)** de todas las imágenes necesarias:
  1. `mongo:latest`
  2. `postgres:16`
  3. `prom/prometheus:latest`
  4. `gcr.io/cadvisor/cadvisor:latest`
  5. `prom/node-exporter:latest`
  6. `alpine:latest`

### Punto Crítico D: Esquema Estricto del CSV de Resultados
El documento universitario exige un esquema inalterable de 14 columnas:
`timestamp_epoch,engine,profile,query_id,concurrency,run_number,throughput_qps,latency_p50_ms,latency_p95_ms,latency_p99_ms,cpu_throttled_seconds,max_rss_mb,disk_spill,status`
* **Matriz oficial (sección 6 del PDF):** 36 celdas = 2 motores × 3 perfiles × 2 queries (Q1/Q2) × 3 concurrencias; 3 repeticiones por celda = **108 corridas**.
* Q2 usa una configuración fija por motor (`allowDiskUse: false` en MongoDB; `work_mem = '4MB'` en PostgreSQL); las variantes alternativas no duplican escenarios.
* Q2_SORT_ALL y cualquier otro escenario extendido se excluyen de la matriz, salvo aprobación posterior explícita. El archivo `mediciones.csv` conservará las 14 columnas obligatorias.
* `disk_spill` se obtiene de métricas del motor, no se infiere a partir de la variante solicitada.
