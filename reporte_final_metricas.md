# Reporte técnico de métricas (análisis parcial)

## Alcance y estado

La matriz aprobada del playbook tiene 108 claves (2 motores × 3 perfiles × Q1/Q2 × concurrencias 1/10/50 × 3 repeticiones). Este análisis usa únicamente las filas `SUCCESS`, deduplicadas por clave; conserva los resultados fallidos para contabilizar y documentar las incidencias. No se considera que la matriz esté completa ni se hace una conclusión estadística definitiva.

- Claves esperadas: 108.
- Claves con al menos un resultado `SUCCESS`: 99.
- Claves sin resultado `SUCCESS`: 9.
- Filas de intentos en el CSV: 109 (99 `SUCCESS`, 9 `ABORTED`, 1 otros estados fallidos).
- Ventana de pared registrada: aproximadamente 15 h 44 min desde el primer aborto de arranque hasta el cierre del log; incluye recreaciones, esperas, abortos y reanudaciones, no solo medición.
- Celdas comparables completas (ambos motores, tres repeticiones por celda): 15/18.
- Fuente: [`mediciones.csv`](mediciones.csv). Resúmenes reproducibles: [`resumen_por_celda.csv`](analisis/resumen_por_celda.csv) y [`resumen_por_motor_query.csv`](analisis/resumen_por_motor_query.csv).

## 1. Especificaciones del host y entorno Docker

Según la auditoría documentada, el host es Windows con backend WSL2 x86_64; Docker dispone de 8 CPU y 5.635 GiB, con cgroups v2. Los perfiles de contenedor son A (4 CPU/4096 MiB), B (2 CPU/2048 MiB) y C (1 CPU/1024 MiB), con swap igual al límite de memoria. Los motores son MongoDB y PostgreSQL 16; Prometheus, cAdvisor y Node Exporter recolectan telemetría. La matriz encontró una limitación práctica de memoria compartida de PostgreSQL, descrita en la sección 6.

## 2. Método de medición y baseline

Cada corrida usa 60 s de warmup, 300 s de medición y 60 s de cooldown; se limpia la caché entre escenarios. Q1 evalúa expansión/filtrado/agrupación; Q2 devuelve Top-1000. La configuración fija de Q2 es MongoDB `allowDiskUse=false` y PostgreSQL `work_mem=4MB`. Los valores consolidados son medianas de repeticiones exitosas; no se imputan los intentos fallidos ni se mezclan variantes preparatorias. El baseline es el perfil A (4 CPU/4 GiB). Su verificación es parcial: hay 33/36 repeticiones `SUCCESS` (11/12 combinaciones completas); faltan las tres repeticiones PostgreSQL/Q1/concurrencia 50. No se calcula significancia estadística con tres repeticiones y datos faltantes.

El límite de medición detiene la admisión de consultas después de 300 s, pero el runner espera a que terminen las consultas en curso antes de calcular los KPIs. Por ello, algunas latencias de cola superan los 300 s nominales; las tres repeticiones MongoDB/Q2/perfil C/concurrencia 50 reportaron P99 entre 481.17 y 515.10 s. El throughput usa el tiempo transcurrido hasta completar esos trabajadores, según el runner.

## 3. Resultados consolidados

Las siguientes medianas agrupan las corridas `SUCCESS` de cada motor y query a través de perfiles y concurrencias; `SUCCESS/Esperadas` hace visible la cobertura. Son descriptivas y no deben interpretarse como una comparación balanceada cuando el conteo sea menor al esperado.

| Motor | Query | SUCCESS | Esperadas | QPS mediana | P95 mediana (ms) | P99 mediana (ms) | Throttling mediano (s) | RSS máximo mediano (MiB) | Corridas con spill |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mongodb | q1 | 27 | 27 | 0.46 | 21115.95 | 22203.28 | 0.00 | 705.41 | 0 |
| mongodb | q2 | 27 | 27 | 0.40 | 17301.43 | 17802.47 | 0.00 | 694.97 | 0 |
| postgresql | q1 | 18 | 27 | 0.07 | 88854.56 | 91029.41 | 0.00 | 312.92 | 18 |
| postgresql | q2 | 27 | 27 | 2.04 | 8312.53 | 8911.99 | 0.00 | 172.47 | 0 |

Los valores por perfil, concurrencia y repetición están disponibles en [`resumen_por_celda.csv`](analisis/resumen_por_celda.csv); se recomienda usar esa tabla para interpretaciones condicionadas por la carga, no solo el agregado anterior.

## 4. Análisis gráfico

- [Latencia P99 vs concurrencia](analisis/graficas/latencia_p99_concurrencia.png): mediana por celda, separada por query y perfil; cada punto indica las repeticiones válidas de tres.
- [CPU throttling vs throughput](analisis/graficas/throttling_vs_throughput.png): una observación por corrida exitosa.
- [RSS a lo largo del experimento](analisis/graficas/rss_tiempo.png): Historia RSS de Prometheus (máximo por contenedor, muestras cada 15 s).

## 5. Comparación de planes de ejecución

Los planes guardados en [`Contexto/09_planes_de_ejecucion_explain.md`](Contexto/09_planes_de_ejecucion_explain.md) son evidencias de `EXPLAIN`/`executionStats` tomadas en la fase preparatoria, no mediciones de ejecución individuales de las 108 corridas.

- **Q1 en MongoDB:** `COLLSCAN`, 500,000 documentos examinados; el explain almacenado informa aproximadamente 2,571 ms. El pipeline expande `items` y agrupa resultados.
- **Q1 en PostgreSQL:** `Parallel Seq Scan` sobre 500,000 filas, expansión con `jsonb_array_elements` y `GroupAggregate`; costo estimado raíz 381,080.71..3,267,845.83. El plan reporta 14,550 buffers shared hit, 84,544 read, 220,386 temp read y 220,638 temp written (bloques), ordenamiento `external merge` y 7,024 ms de ejecución.
- **Q2 Top-1000 en MongoDB:** plan con `IXSCAN` del índice `timestamp`, `FETCH` por estado y `SORT` con límite 1000; `executionStats` reporta 293,342 claves/documentos examinados y aproximadamente 903 ms. MongoDB no expone en este explain un estimador de costo directamente comparable con el costo del planificador PostgreSQL ni contadores shared/temp buffers equivalentes.
- **Q2 Top-1000 en PostgreSQL:** costo estimado raíz 105,729.65..105,810.62; `Parallel Seq Scan`, buffers shared hit=14,644/read=84,448 y ordenamiento Top-N (`top-N heapsort`) en alrededor de 273 kB por worker, sin spill temporal en este plan. Ejecución: 299 ms con `work_mem=4MB`. `work_mem=64MB` y Q2_SORT_ALL son evidencia auxiliar, no parte de la matriz oficial.

Las duraciones EXPLAIN corresponden a una ejecución de plan con su propio estado de caché y no son directamente equivalentes al throughput concurrente del benchmark.

## 6. Memoria, spill y throttling

La incidencia principal fue PostgreSQL Q1 a concurrencia 50: el contenedor no pudo ampliar un segmento de memoria compartida de 1 MiB y reportó `No space left on device`. El error apareció durante warmup o medición bajo el `/dev/shm` predeterminado; afectó las tres repeticiones en los perfiles A/B/C. Nueve claves quedaron sin un resultado `SUCCESS`: ocho con último intento `ABORTED` y una con `PARTIAL_FAILURE`. La fila abortada temprana de MongoDB Q1/repetición 1 tiene una fila `SUCCESS` posterior y por ello esa clave sí cuenta como exitosa. La ejecución se considera cerrada: no se realizaron nuevas corridas ni reintentos adicionales, no se cambió el protocolo y no se modificó `shm_size`.

Las tres corridas MongoDB/Q2/perfil C/concurrencia 50 tuvieron P99 mayor a la ventana nominal de 300 s; el runner esperó la terminación de los trabajadores activos. Se conservan como resultados medidos, y su duración mayor debe tenerse en cuenta al interpretar throughput y latencias.

La columna `disk_spill` indica si se observó escritura temporal/spill durante la corrida; las tablas de resumen cuentan estos casos solo entre ejecuciones `SUCCESS`. El throttling y RSS son métricas observadas por el recolector; ausencia de throttling reportado no demuestra ausencia de presión de CPU. No se infieren mediciones para filas abortadas.

Claves incompletas:
- `postgresql / PROFILE_A_BASELINE / Q1 / concurrencia 50 / repetición 1`
- `postgresql / PROFILE_A_BASELINE / Q1 / concurrencia 50 / repetición 2`
- `postgresql / PROFILE_A_BASELINE / Q1 / concurrencia 50 / repetición 3`
- `postgresql / PROFILE_B_MEDIUM / Q1 / concurrencia 50 / repetición 1`
- `postgresql / PROFILE_B_MEDIUM / Q1 / concurrencia 50 / repetición 2`
- `postgresql / PROFILE_B_MEDIUM / Q1 / concurrencia 50 / repetición 3`
- `postgresql / PROFILE_C_SEVERE / Q1 / concurrencia 50 / repetición 1`
- `postgresql / PROFILE_C_SEVERE / Q1 / concurrencia 50 / repetición 2`
- `postgresql / PROFILE_C_SEVERE / Q1 / concurrencia 50 / repetición 3`

## 7. Recomendaciones técnicas

1. Tratar estas conclusiones como preliminares y declarar explícitamente que 9/108 claves carecen de resultado válido.
2. No usar PostgreSQL Q1/concurrencia 50 para una comparación directa con MongoDB hasta contar con mediciones válidas bajo un protocolo revisado.
3. Si se autoriza una repetición futura, registrar primero como nueva versión de protocolo el tamaño de `/dev/shm`, comprobarlo en el contenedor antes de la corrida y reejecutar todas las comparaciones afectadas de forma consistente; no sobrescribir el CSV actual.
4. Conservar el CSV, logs de ejecución/incidencias, configuración Compose, planes EXPLAIN y versiones de contenedores junto con cualquier entrega.
5. Evitar extrapolar resultados del host local a producción cloud; repetir bajo límites, almacenamiento, red y versión de motor equivalentes al destino.

## Estado de cumplimiento de los entregables del playbook

| Entregable | Estado | Evidencia o limitación |
| --- | --- | --- |
| 1. Especificaciones del host y entorno Docker | Completo | Host, recursos Docker/cgroups, perfiles y stack de telemetría descritos. |
| 2. Método de medición y verificación del baseline | Parcial | Protocolo y perfil A identificados; baseline con 33/36 repeticiones válidas. Las tres faltantes impiden verificarlo completamente. |
| 3. Resultados consolidados (throughput, P95/P99 y throttling) | Parcial | Métricas consolidadas de ejecuciones `SUCCESS`; PostgreSQL/Q1 conserva 18/27 resultados y no permite una comparación balanceada. |
| 4. Análisis gráfico | Completo | Se incluyen las tres gráficas solicitadas: P99/concurrencia, throttling/throughput y RSS. |
| 5. Comparación de planes de ejecución | Completo | Se comparan Q1/Q2 para ambos motores; se explicitan las métricas que MongoDB no expone de forma comparable. |
| 6. Interpretación de memoria, spill y throttling | Parcial | Se documentan la incidencia de `/dev/shm` y las métricas observadas; no se atribuyen valores a las nueve claves sin `SUCCESS`. |
| 7. Recomendaciones técnicas para despliegues en la nube | Completo | Se incluyen cautelas de protocolo, comparabilidad, conservación de evidencias y límites de extrapolación. |

## Artefactos y reproducibilidad

Ejecutar desde la raíz del proyecto:

```powershell
& .\venv\Scripts\python.exe .\analisis\graficador.py
```

El script vuelve a generar los resúmenes y las gráficas. Consulta el historial RSS de Prometheus para el intervalo de la matriz; si la API ya no conserva esas muestras, genera una visualización alternativa de los máximos RSS por corrida registrados en el CSV e identifica expresamente esa limitación. La ejecución de ese script solo regenera artefactos de análisis; no vuelve a ejecutar benchmarks.
