#!/usr/bin/env python3
"""
Motor de Concurrencia y Runner de Benchmarks
Experimento IT2iD (2026) - Universidad Politécnica de Chiapas
Soporta concurrencias de 1, 10 y 50 clientes.
Calcula Throughput (QPS), Latencias P50, P95, P99 y registra telemetría de Prometheus.
Escribe directamente en el esquema CSV de 14 columnas reglamentario.
"""

import os
import sys
import time
import argparse
import threading
import numpy as np
import pymongo
from pymongo.errors import OperationFailure
import psycopg2

# Importar recolector de telemetría de Prometheus
from metrics_collector import (
    get_cpu_throttled_seconds,
    get_max_memory_rss_mb,
    get_oom_events,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Configuraciones de conexión
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "benchmark_db"
PG_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "user": "benchmark",
    "password": "benchmark",
    "dbname": "benchmark_db"
}

# Consultas pre-compiladas
MONGO_Q1_PIPELINE = [
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

MONGO_Q2_PIPELINE = [
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

MONGO_Q2_SORT_ALL_PIPELINE = [
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

PG_Q1_SQL = """
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

PG_Q2_SQL = """
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

PG_Q2_SORT_ALL_SQL = """
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
) AS ranked_orders;
"""

CSV_HEADER = (
    "timestamp_epoch,engine,profile,query_id,concurrency,run_number,"
    "throughput_qps,latency_p50_ms,latency_p95_ms,latency_p99_ms,"
    "cpu_throttled_seconds,max_rss_mb,disk_spill,status\n"
)

def ensure_csv_header(file_path: str):
    """Crea el CSV con su encabezado oficial si no existe."""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(CSV_HEADER)

def mongo_pipeline_for(query_id):
    if query_id == "q1":
        return MONGO_Q1_PIPELINE
    if query_id == "q2":
        return MONGO_Q2_PIPELINE
    return MONGO_Q2_SORT_ALL_PIPELINE

def postgres_query_for(query_id):
    if query_id == "q1":
        return PG_Q1_SQL
    if query_id == "q2":
        return PG_Q2_SQL
    return PG_Q2_SORT_ALL_SQL

def _disk_spill_indicator(value):
    if isinstance(value, dict):
        indicators = []
        if isinstance(value.get("usedDisk"), bool):
            indicators.append(value["usedDisk"])
        if isinstance(value.get("spills"), (int, float)):
            indicators.append(value["spills"] > 0)
        indicators.extend(
            result
            for child in value.values()
            if (result := _disk_spill_indicator(child)) is not None
        )
        return any(indicators) if indicators else None
    if isinstance(value, list):
        indicators = [
            result
            for child in value
            if (result := _disk_spill_indicator(child)) is not None
        ]
        return any(indicators) if indicators else None
    return None

def get_postgres_temp_bytes():
    conn = psycopg2.connect(**PG_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_stat_clear_snapshot();")
            cur.execute(
                "SELECT temp_bytes FROM pg_stat_database "
                "WHERE datname = current_database();"
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        raise RuntimeError("PostgreSQL did not return temp_bytes for the benchmark database")
    return int(row[0])

def get_mongo_disk_spill(query_id, allow_disk_use):
    client = pymongo.MongoClient(MONGO_URI)
    try:
        command = {
            "aggregate": "orders",
            "pipeline": mongo_pipeline_for(query_id),
            "cursor": {},
            "allowDiskUse": allow_disk_use,
        }
        try:
            explain = client[MONGO_DB].command({
                "explain": command,
                "verbosity": "executionStats",
            })
        except OperationFailure as exc:
            if exc.code == 292:
                return False
            raise
        spill_detected = _disk_spill_indicator(explain)
        if spill_detected is None:
            raise RuntimeError(
                "MongoDB explain did not expose usedDisk/spills; refusing to record an inferred value"
            )
        return spill_detected
    finally:
        client.close()

def worker_mongo(client, query_id, allow_disk_use, stop_event, latencies_list, errors, lock):
    try:
        coll = client[MONGO_DB]["orders"]
        pipeline = mongo_pipeline_for(query_id)

        while not stop_event.is_set():
            t0 = time.perf_counter()
            try:
                options = {"allowDiskUse": allow_disk_use} if query_id != "q1" else {}
                _ = list(coll.aggregate(pipeline, **options))
                dur_ms = (time.perf_counter() - t0) * 1000.0
                with lock:
                    latencies_list.append(dur_ms)
            except Exception as exc:
                with lock:
                    if len(errors) < 10:
                        errors.append(f"MongoDB: {type(exc).__name__}: {exc}")
                if isinstance(exc, OperationFailure) and exc.code == 292:
                    stop_event.set()
                    break
                time.sleep(0.05)
    finally:
        client.close()

def worker_postgres(pg_config, query_id, work_mem, stop_event, latencies_list, errors, lock):
    conn = None
    try:
        conn = psycopg2.connect(**pg_config)
        conn.autocommit = True
        cur = conn.cursor()
        if work_mem:
            if work_mem not in {"4MB", "64MB"}:
                raise ValueError(f"Unsupported work_mem value: {work_mem}")
            cur.execute("SELECT set_config('work_mem', %s, false);", (work_mem,))
        if query_id.startswith("q2_sort_all_"):
            cur.execute("SET max_parallel_workers_per_gather = 0;")
        sql = postgres_query_for(query_id)

        while not stop_event.is_set():
            t0 = time.perf_counter()
            try:
                cur.execute(sql)
                _ = cur.fetchall()
                dur_ms = (time.perf_counter() - t0) * 1000.0
                with lock:
                    latencies_list.append(dur_ms)
            except Exception as exc:
                with lock:
                    if len(errors) < 10:
                        errors.append(f"PostgreSQL: {type(exc).__name__}: {exc}")
                if "memory" in str(exc).lower():
                    stop_event.set()
                    break
                time.sleep(0.05)
        cur.close()
    except Exception as exc:
        with lock:
            if len(errors) < 10:
                errors.append(f"PostgreSQL connection: {type(exc).__name__}: {exc}")
    finally:
        if conn is not None:
            conn.close()

def run_benchmark(engine, query_id, concurrency, duration, warmup, profile, run_number, variant, output_csv):
    container_name = "mongodb" if engine == "mongodb" else "postgres"
    print(f"==================================================")
    print(f"[*] EJECUTANDO BENCHMARK:")
    print(f"    Motor: {engine.upper()} | Query: {query_id.upper()} | Concurrencia: {concurrency}")
    print(f"    Perfil: {profile} | Corrida: #{run_number} | Duracion: {duration}s")
    print(f"==================================================")

    # 1. Warmup (Calentamiento de caches si > 0)
    if warmup > 0:
        print(f"[*] Fase de Warmup ({warmup}s)...")
        stop_warmup = threading.Event()
        w_lat = []
        w_errors = []
        w_lock = threading.Lock()
        threads = []
        for _ in range(concurrency):
            if engine == "mongodb":
                mc = pymongo.MongoClient(MONGO_URI)
                t = threading.Thread(target=worker_mongo, args=(mc, query_id, variant == "allowDiskUse_true", stop_warmup, w_lat, w_errors, w_lock))
            else:
                wm = "4MB" if variant == "work_mem_4MB" else "64MB" if variant == "work_mem_64MB" else None
                t = threading.Thread(target=worker_postgres, args=(PG_CONFIG, query_id, wm, stop_warmup, w_lat, w_errors, w_lock))
            threads.append(t)
            t.start()
        time.sleep(warmup)
        stop_warmup.set()
        for t in threads:
            t.join()
        print(f"[+] Warmup finalizado ({len(w_lat)} consultas previas ejecutadas).")
        if w_errors:
            is_expected_memory_limit = any(
                "memory limit" in error.lower()
                for error in w_errors
            )
            if is_expected_memory_limit:
                print("[!] El warmup encontró el límite de memoria configurado; la corrida medirá ese fallo.")
            else:
                raise RuntimeError(f"Warmup query failed: {w_errors[0]}")

    # 2. Telemetría inicial
    print(f"[*] Iniciando medicion activa ({duration}s)...")
    t_start_epoch = int(time.time())
    throttled_start = get_cpu_throttled_seconds(container_name)
    oom_start = get_oom_events(container_name)
    postgres_temp_start = get_postgres_temp_bytes() if engine == "postgresql" else None

    # 3. Lanzar clientes concurrentes
    stop_measurement = threading.Event()
    latencies = []
    errors = []
    lock = threading.Lock()
    threads = []

    t_begin = time.perf_counter()
    for _ in range(concurrency):
        if engine == "mongodb":
            mc = pymongo.MongoClient(MONGO_URI)
            allow_disk = variant == "allowDiskUse_true"
            t = threading.Thread(target=worker_mongo, args=(mc, query_id, allow_disk, stop_measurement, latencies, errors, lock))
        else:
            wm = "4MB" if variant == "work_mem_4MB" else "64MB" if variant == "work_mem_64MB" else None
            t = threading.Thread(target=worker_postgres, args=(PG_CONFIG, query_id, wm, stop_measurement, latencies, errors, lock))
        threads.append(t)
        t.start()

    time.sleep(duration)
    stop_measurement.set()

    for t in threads:
        t.join()

    total_time = time.perf_counter() - t_begin

    # 4. Telemetría final
    measurement_end_epoch = time.time()
    throttled_end = get_cpu_throttled_seconds(container_name)
    max_rss_mb = get_max_memory_rss_mb(container_name, t_start_epoch, measurement_end_epoch)
    oom_end = get_oom_events(container_name)

    cpu_throttled_sec = max(0.0, round(throttled_end - throttled_start, 4))
    is_oom = oom_end > oom_start

    # 5. Cálculo de KPIs
    total_q = len(latencies)
    qps = round(total_q / total_time, 2) if total_time > 0 else 0.0

    if latencies:
        p50 = round(float(np.percentile(latencies, 50)), 2)
        p95 = round(float(np.percentile(latencies, 95)), 2)
        p99 = round(float(np.percentile(latencies, 99)), 2)
    else:
        p50, p95, p99 = 0.0, 0.0, 0.0

    # Detección de volcado a disco (disk_spill)
    if engine == "mongodb":
        disk_spill = get_mongo_disk_spill(
            query_id, variant == "allowDiskUse_true"
        ) if query_id != "q1" else get_mongo_disk_spill(query_id, True)
    else:
        postgres_temp_end = get_postgres_temp_bytes()
        disk_spill = postgres_temp_end > postgres_temp_start

    memory_limit_failure = any(
        "exceeded memory limit" in error.lower()
        or "memory limit" in error.lower()
        for error in errors
    )
    if is_oom:
        status = "OOM_KILLED"
    elif memory_limit_failure:
        status = "FAIL_MEMORY_LIMIT"
    elif errors and total_q == 0:
        status = "FAIL_QUERY_ERROR"
    elif errors:
        status = "PARTIAL_FAILURE"
    else:
        status = "SUCCESS" if total_q > 0 else "FAIL_NO_QUERIES"

    # 6. Mostrar resultados
    print(f"\n==================================================")
    print(f"📊 RESULTADOS DE LA MEDICION:")
    print(f"    Throughput: {qps:,.2f} queries/s ({total_q:,} consultas en {total_time:.1f}s)")
    print(f"    Latencia P50: {p50} ms | P95: {p95} ms | P99: {p99} ms")
    print(f"    CPU Throttled: {cpu_throttled_sec} s | Max RAM RSS: {max_rss_mb} MB")
    print(f"    Disk Spill: {disk_spill} | Status: {status}")
    if errors:
        print(f"    Errores de consulta: {len(errors)} (primero: {errors[0]})")
    print(f"==================================================")

    # 7. Escribir fila en CSV
    if output_csv:
        ensure_csv_header(output_csv)
        row = f"{t_start_epoch},{engine},{profile},{query_id},{concurrency},{run_number},{qps},{p50},{p95},{p99},{cpu_throttled_sec},{max_rss_mb},{disk_spill},{status}\n"
        with open(output_csv, "a", encoding="utf-8") as f:
            f.write(row)
        print(f"[+] Registro guardado exitosamente en: {output_csv}\n")

    return {
        "throughput_qps": qps,
        "p50": p50,
        "p95": p95,
        "p99": p99,
        "cpu_throttled": cpu_throttled_sec,
        "max_rss": max_rss_mb,
        "disk_spill": disk_spill,
        "status": status
    }

def main():
    parser = argparse.ArgumentParser(description="Runner de Benchmarks IT2iD 2026")
    parser.add_argument("--engine", choices=["mongodb", "postgresql"], required=True)
    parser.add_argument(
        "--query",
        choices=["q1", "q2", "q2_sort_all_low", "q2_sort_all_high"],
        required=True
    )
    parser.add_argument("--concurrency", type=int, choices=[1, 10, 50], default=1)
    parser.add_argument("--duration", type=int, default=300, help="Duracion en segundos de la medicion")
    parser.add_argument("--warmup", type=int, default=60, help="Duracion en segundos del warmup")
    parser.add_argument("--profile", type=str, default="PROFILE_A_BASELINE")
    parser.add_argument("--run-number", type=int, default=1)
    parser.add_argument("--variant", type=str, default="", help="Variante de memoria para Q2")
    parser.add_argument("--output-csv", type=str, default="mediciones.csv")

    args = parser.parse_args()
    run_benchmark(
        engine=args.engine,
        query_id=args.query,
        concurrency=args.concurrency,
        duration=args.duration,
        warmup=args.warmup,
        profile=args.profile,
        run_number=args.run_number,
        variant=args.variant,
        output_csv=args.output_csv
    )

if __name__ == "__main__":
    main()
