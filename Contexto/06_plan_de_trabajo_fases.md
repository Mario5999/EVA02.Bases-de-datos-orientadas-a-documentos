# 06. Plan de Trabajo Detallado (Checklist Paso a Paso)

Este documento es nuestra guía de ruta viva. Contiene cada paso desglosado desde cero, explicando **qué es**, **por qué se hace** y con casillas de verificación `[ ]` que iremos marcando `[x]` conforme avancemos juntos.

---

## 📌 Resumen de Fases
* [x] **Fase 1:** Preparación del Entorno y Dependencias
* [x] **Fase 2:** Generador del Dataset Sintético (500,000 registros)
* [x] **Fase 3:** Infraestructura Docker y Perfiles de Recursos
* [x] **Fase 4:** Ingesta de Datos e Indexación en MongoDB y PostgreSQL
* [x] **Fase 5:** Creación y Validación de Consultas Q1 y Q2
* [x] **Fase 6:** Runner de Pruebas de Carga y Telemetría con Prometheus
* [ ] **Fase 7:** Automatización de la matriz oficial (108 ejecuciones)
* [x] **Fase 8:** Análisis y reporte parcial de las corridas disponibles (matriz incompleta)

---

## 🔹 Fase 1: Preparación del Entorno y Dependencias
El objetivo de esta fase es dejar tu computadora con todas las herramientas listas para que nada falle más adelante.

- [x] **Paso 1.1: Explicación de las herramientas base**
  * *¿Qué es?* Comprender qué función cumple Python, Docker Desktop y Node.js en este proyecto.
  * *¿Por qué se hace?* Para que tengas total control mental de qué programa se encarga de cada parte.
- [x] **Paso 1.2: Creación del archivo `requirements.txt`**
  * *¿Qué es?* Una lista con los nombres exactos de las librerías de Python que utilizaremos (`pymongo`, `psycopg2-binary`, `faker`, `requests`, `pandas`, `matplotlib`).
  * *¿Por qué se hace?* Para instalar todo de forma estandarizada y reproducible.
- [x] **Paso 1.3: Creación y activación del entorno virtual de Python (`venv`)**
  * *¿Qué es?* Una "caja de arena" aislada en tu computadora donde se instalarán las librerías del proyecto sin afectar tus otros programas de Python.
  * *¿Por qué se hace?* Buenas prácticas de ingeniería de software para evitar conflictos de versiones.
- [x] **Paso 1.4: Instalación de las librerías de Python**
  * *¿Qué es?* Ejecutar `pip install -r requirements.txt`.
  * *¿Por qué se hace?* Para que nuestros scripts puedan conectarse a las bases de datos y procesar datos. Los paquetes requeridos, incluido `numpy`, están presentes en el `venv`.
- [x] **Paso 1.5: Verificación de configuración en Docker Desktop**
  * *¿Qué es?* Revisar en los ajustes de Docker que el motor tenga asignados al menos 4 núcleos de CPU y al menos 4 GB de memoria RAM.
  * *¿Por qué se hace?* El *Perfil A (Baseline)* exige 4 CPUs y 4 GB de RAM. Si Docker tuviera menos, no podríamos probar ese escenario.

---

## 🔹 Fase 2: Generador del Dataset Sintético (500,000 registros)
Crearemos los datos de prueba que simularán una tienda en línea real.

- [x] **Paso 2.1: Explicación de "Datos Sintéticos" y estructura anidada**
  * *¿Qué es?* Explicar por qué generamos datos falsos en vez de buscar una base real y cómo se estructuran los 3 niveles de anidamiento (orden -> cliente -> dirección/items).
  * *¿Por qué se hace?* Para garantizar que el dataset cumpla exactamente las reglas del profesor (promedio 3 items por orden, UUIDs, ISO-8601, etc.).
- [x] **Paso 2.2: Programación de `synthetic_data_generator.py`**
  * *¿Qué es?* Un script en Python optimizado para generar 500,000 registros sin trabar tu computadora.
  * *¿Por qué se hace?* Si intentáramos meter 500,000 JSONs en la memoria RAM al mismo tiempo, la computadora se quedaría sin memoria. Usaremos escritura por lotes (*batch streaming* directo a disco).
- [x] **Paso 2.3: Regeneración del archivo `dataset/orders_500k.jsonl`**
  * *¿Qué es?* Correr el script y esperar a que genere el archivo en disco (formato JSON Lines).
  * *¿Por qué se hace?* Será la fuente única de la verdad con la que alimentaremos tanto a MongoDB como a PostgreSQL para que la comparación sea 100% justa.
- [x] **Paso 2.4: Inspección y validación del dataset generado**
  * *¿Qué es?* Comprobar que el archivo tenga exactamente 500,000 líneas, revisar el tamaño en disco (~250-400 MB) y verificar un par de registros al azar.
  * Validar también que el promedio observado de ítems sea 3 ± 0.01.

---

## 🔹 Fase 3: Infraestructura Docker y Perfiles de Recursos
Montaremos los servidores de base de datos y los sistemas de medición con sus límites estrictos.

- [x] **Paso 3.1: Explicación de cómo Docker impone límites (`cgroups v2`)**
  * *¿Qué es?* Entender cómo el sistema operativo le quita o le frena el procesador a un contenedor (*CFS throttling*) y qué pasa cuando se acaba la RAM (*OOM Kill*).
- [x] **Paso 3.2: Configuración de Prometheus (`configs/prometheus.yml`)**
  * *¿Qué es?* El archivo de configuración de Prometheus indicándole que recolecte métricas cada 1 segundo (`scrape_interval: 1s`).
- [x] **Paso 3.3: Creación del `docker-compose.yml` parametrizado**
  * *¿Qué es?* El archivo maestro que levantará MongoDB, PostgreSQL, cAdvisor, Node Exporter y Prometheus.
  * *¿Por qué se hace?* Permite cambiar entre el Perfil A (4 CPU, 4GB), Perfil B (2 CPU, 2GB) y Perfil C (1 CPU, 1GB con throttling) mediante variables de entorno fácilmente.
- [x] **Paso 3.4: Aplicación y verificación con límites revisados**
  * *¿Qué es?* Ejecutar `docker compose up -d` y verificar que todos los servicios estén en estado "Up".
  * Verificado: ambos motores operan con 4 CPU, 4096 MiB de memoria y límite de swap igual a la memoria; cgroups v2 y objetivos de Prometheus activos.
- [x] **Paso 3.5: Verificación de acceso a paneles de métricas**
  * *¿Qué es?* Abrir en el navegador local cAdvisor (puerto host 8085) y Prometheus (puerto 9090) para confirmar que están leyendo los cgroups del contenedor.

---

## 🔹 Fase 4: Ingesta de Datos e Indexación en MongoDB y PostgreSQL
Poblaremos ambas bases de datos con los mismos 500,000 registros y crearemos los índices obligatorios.

- [x] **Paso 4.1: Explicación de índices y por qué no indexamos todo**
  * *¿Qué es?* Entender qué es un índice B-Tree y por qué el documento pide indexar solo `timestamp` y `order_id`, dejando otros campos sin índice para forzar a las bases a trabajar duro.
- [x] **Paso 4.2: Script de carga para MongoDB (`scripts/load_mongo.py`)**
  * *¿Qué es?* Script en Python que lee el archivo `orders_500k.jsonl` en bloques de 5,000 documentos y los inserta en la colección `orders`.
- [x] **Paso 4.3: Script de carga para PostgreSQL (`scripts/load_postgres.py`)**
  * *¿Qué es?* Script que crea la tabla `orders (id UUID PRIMARY KEY, data JSONB)` y carga los documentos usando inserción eficiente en bloque.
- [x] **Paso 4.4: Creación de índices específicos**
  * *MongoDB:* Crear índice en `timestamp` y `order_id`.
  * *PostgreSQL:* Clave primaria en `id` e índice B-Tree sobre `(data->>'timestamp')`.
- [x] **Paso 4.5: Auditoría de conteo y consistencia**
  * *¿Qué es?* Lanzar un `count()` en ambas bases para verificar que tengan exactamente 500,000 registros idénticos.
  * Auditoría actual: 500,000 registros en ambos motores; promedio 3.0009 ítems; índices requeridos presentes.

---

## 🔹 Fase 5: Creación y Validación de Consultas Q1 y Q2
Programaremos y probaremos las dos consultas de laboratorio.

- [x] **Paso 5.1: Explicación a fondo de Q1 (Saturación de CPU)**
  * *¿Qué es?* Desarmar el arreglo de productos (`$unwind` en Mongo, `jsonb_array_elements` en Postgres), filtrar precios > 50 y calcular ingresos agrupados por país y categoría.
- [x] **Paso 5.2: Creación de archivos de consulta Q1**
  * Guardar `queries/mongo_q1.js` y `queries/postgres_q1.sql`.
- [x] **Paso 5.3: Explicación a fondo de Q2 (Estrés de Memoria / Top-K)**
  * *¿Qué es?* Filtrar órdenes completadas en 2026 y ordenar por total descendente para traer las 1,000 mejores sin índice de ordenamiento.
- [x] **Paso 5.4: Configuración de variantes de memoria**
  * La matriz oficial ejecuta Q2 Top-1000 una vez por escenario: MongoDB `allowDiskUse: false` y PostgreSQL `work_mem = '4MB'`.
  * Las variantes `allowDiskUse: true` y `work_mem = '64MB'`, así como Q2_SORT_ALL, solo se usaron en validaciones preparatorias y no forman parte de la matriz oficial.
- [x] **Paso 5.5: Actualización de los Planes de Ejecución**
  * *¿Qué es?* Correr `explain("executionStats")` en MongoDB y `EXPLAIN (ANALYZE, BUFFERS)` en PostgreSQL para ver paso a paso cómo razona cada motor antes de la prueba masiva.
  * EXPLAIN regenerados para Q1, Q2 Top-1000 y pruebas auxiliares de Q2_SORT_ALL; estas últimas no se incluyen en la matriz oficial.

---

## 🔹 Fase 6: Runner de Pruebas de Carga y Telemetría con Prometheus
Construiremos el programa que enviará las oleadas de consultas y tomará el tiempo exacto.

- [x] **Paso 6.1: Explicación del protocolo científico de medición**
  * *¿Qué es?* Comprender por qué es obligatorio tener:
    1. Calentamiento (*Warmup* de 60s) para llenar cachés de memoria.
    2. Medición activa (300s / 5 minutos) donde se toman los datos reales.
    3. Enfriamiento (*Cooldown* de 60s) para estabilizar el sistema.
- [x] **Paso 6.2: Módulo recolector de métricas (`benchmark_runner/metrics_collector.py`)**
  * *¿Qué es?* Script que consulta la API de Prometheus para extraer:
    * `container_cpu_cfs_throttled_seconds_total` (segundos de CPU estrangulada).
    * `container_memory_rss_bytes` (memoria RAM real ocupada).
    * Detección de caída por falta de memoria (`oom_killed`).
  * El código está implementado y pasó revisión sintáctica; falta validar su comportamiento en el piloto actualizado.
- [x] **Paso 6.3: Motor de concurrencia (`benchmark_runner/runner.py`)**
  * *¿Qué es?* Script en Python que lanza hilos o clientes concurrentes (1, 10 y 50 clientes) atacando la base de datos de manera ininterrumpida y calculando latencias P50, P95 y P99 en milisegundos.
  * El código está implementado y pasó revisión sintáctica; falta validarlo en el piloto actualizado.
- [x] **Paso 6.4: Prueba piloto de validación**
  * *¿Qué es?* Ejecutar una prueba corta de 30 segundos con 1 cliente para verificar la versión actualizada del runner y la telemetría.
  * Piloto realizado en ambos motores para Q1, concurrencia 1: MongoDB y PostgreSQL finalizaron con estado `SUCCESS`; se validaron las 14 columnas del CSV.

---

## 🔹 Fase 7: Automatización de la Matriz Oficial (108 ejecuciones)
La fase central del laboratorio: poner a competir a ambos motores en todas las combinaciones.

**Diseño oficial (sección 6 del playbook):** 36 celdas = 2 motores × 3 perfiles × 2 queries (Q1/Q2) × 3 concurrencias; con 3 repeticiones por celda, son **108 corridas**. Por motor son 54; por perfil de recursos son 36 en ambos motores.

**Configuración Q2:** MongoDB `allowDiskUse: false` y PostgreSQL `work_mem = '4MB'`, fijadas como configuración del escenario y no como factor adicional. `Q2_SORT_ALL`, `allowDiskUse: true` y `work_mem = '64MB'` fueron pruebas preparatorias y quedan fuera de las 108 corridas.

**Estado:** matriz oficial autorizada y ejecutada parcialmente. Se registraron resultados para las 108 claves: 99 `SUCCESS` y 9 claves sin éxito (8 abortadas y 1 con `PARTIAL_FAILURE`). Los fallos se concentran en PostgreSQL Q1 con concurrencia 50 y se asociaron a falta de espacio en `/dev/shm` durante el warmup o la medición. La matriz no se considera completa hasta resolver o documentar formalmente esas claves.

- [x] **Paso 7.1: Definición de la matriz completa**
  * 36 celdas (2 motores × 3 perfiles × 2 queries × 3 concurrencias).
  * 3 repeticiones por celda.
  * Total: **108 corridas experimentales; 54 por motor; 36 por perfil de recursos**.
- [x] **Paso 7.2: Creación del archivo de resultados `mediciones.csv`**
  * *¿Qué es?* El orquestador crea el CSV con las 14 columnas reglamentarias al iniciar la ejecución.
- [x] **Paso 7.3: Creación del script orquestador (`run_benchmarks.ps1`)**
  * *¿Qué es?* El script automático que:
    1. Aplica el perfil de Docker correspondiente (Baseline, Medio o Severo).
    2. Limpia cachés de memoria del host.
    3. Corre el warmup, la medición y el cooldown.
    4. Verifica los datos y objetivos de Prometheus, y guarda cada corrida en el CSV.
  * Para evitar inicios accidentales, requiere `-ConfirmRun`; sin esa opción solo muestra la matriz y duración estimada.
- [ ] **Paso 7.4: Ejecución progresiva de la matriz de pruebas**
  * Correr las combinaciones de manera ordenada, monitoreando la salud de tu equipo.
  * Autorizada por el usuario y procesadas las 108 claves; 99 terminaron `SUCCESS` y 9 requieren atención. El CSV conserva los estados y reintentos.
  * Incidencia: PostgreSQL no pudo ampliar segmentos de memoria compartida (`No space left on device`) en Q1 con concurrencia 50. No se modificaron los límites de recursos ni la configuración de los perfiles.
  * Evidencia: `mediciones.csv`, `mediciones_incidencias.log`, `matriz_108_execution.log` y `matrix_resume_after_pg_shm.log`.

---

## 🔹 Fase 8: Análisis Estadístico, Gráficas y Reporte Técnico
Transformaremos los números brutos en conocimiento científico para tu entrega universitaria.

- **Estado:** análisis reproducible generado a partir de las 99 claves `SUCCESS`. Es parcial porque nueve claves PostgreSQL/Q1/concurrencia 50 siguen sin resultado válido; no es una certificación de la matriz completa.

- [x] **Paso 8.1: Creación del script generador de gráficas (`analisis/graficador.py`)**
  * *¿Qué es?* Script en Python con `pandas` y `matplotlib` que lee `mediciones.csv` y dibuja las gráficas.
- [x] **Paso 8.2: Generación de las gráficas obligatorias**
  * Gráfica 1: Latencia P99 vs Concurrencia (1, 10, 50 clientes).
  * Gráfica 2: CPU Throttling vs Throughput (QPS).
  * Gráfica 3: RSS histórico de Prometheus, agregado por contenedor y muestreado cada 15 s. Si la retención expira, el script cambia a RSS máximo por corrida y lo identifica como aproximación.
- [x] **Paso 8.3: Análisis comparativo de planes de ejecución (`explain`)**
  * Contrastar el uso de buffers, costo estimado y volcado a disco entre Mongo y Postgres.
- [x] **Paso 8.4: Redacción del Reporte Técnico de Métricas (`reporte_final_metricas.md`)**
  * Redactar las 7 secciones completas que pide la rúbrica de la UPChiapas:
    1. Especificaciones del host y entorno Docker.
    2. Método de medición y verificación del baseline.
    3. Resultados consolidados (throughput, P95/P99, tiempo de throttling).
    4. Análisis gráfico.
    5. Comparación profunda de planes de ejecución.
    6. Interpretación de límites de memoria, volcado a disco y throttling de cgroups.
    7. Recomendaciones técnicas para despliegues documentales en la nube.
  * El reporte queda marcado como parcial y conserva explícitamente las nueve claves incompletas; no atribuye métricas a corridas abortadas ni presenta conclusiones finales balanceadas.
  * Artefactos: `reporte_final_metricas.md`, `analisis/resumen_por_celda.csv`, `analisis/resumen_por_motor_query.csv` y las tres PNG en `analisis/graficas/`.
