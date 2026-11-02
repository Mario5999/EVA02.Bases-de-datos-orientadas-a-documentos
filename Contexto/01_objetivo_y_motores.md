# 01. Objetivo General y Motores de Base de Datos

* **Institución:** Universidad Politécnica de Chiapas
* **Carrera:** Ingeniería en Tecnologías de la Información e Innovación Digital (IT2iD)
* **Asignatura:** Bases de Datos en la Nube (2026)
* **Tema:** Medición de métricas en bases documentales: Contención de CPU y memoria en agregaciones JSON

---

## Objetivo General
Medir latencia, rendimiento (throughput) y huella de recursos al ejecutar agregaciones JSON anidadas bajo límites estrictos de CPU (CFS throttling) y memoria con Docker cgroups v2, comparando un motor documental nativo frente a un motor relacional que almacena documentos en formato JSONB.

---

## Preguntas de Investigación (Métricas)
* **M1:** ¿Cómo cambian la latencia P95 y P99 de las agregaciones sobre documentos anidados cuando se limita de forma estricta la CPU y la memoria?
* **M2:** ¿Qué motor usa de forma más eficiente los buffers de ordenamiento y agrupamiento antes de volcar a disco temporal o fallar por falta de memoria (OOM)?
* **M3:** ¿Cuál es la huella de CPU y memoria por cada 1,000 documentos procesados en el motor documental frente al motor con JSONB?

---

## Motores Objetivo

### 1. MongoDB
* **Modelo de datos:** Colección `orders` sin sharding.
* **Motor de almacenamiento:** WiredTiger.
* **Versión:** `latest-stable`.
* **Indexación exigida:** Índice simple en `timestamp` y `order_id`.

### 2. PostgreSQL
* **Modelo de datos:** Tabla `orders (id UUID PRIMARY KEY, data JSONB)`.
* **Versión:** `latest-stable`.
* **Indexación exigida:** Primary Key en `id`; B-Tree sobre `timestamp` extraído del JSONB (`(data->>'timestamp')`).

