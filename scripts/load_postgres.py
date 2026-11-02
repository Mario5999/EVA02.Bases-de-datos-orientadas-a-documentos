#!/usr/bin/env python3
"""
Script de Carga Masiva e Indexación para PostgreSQL
Experimento IT2iD (2026)
Tabla: orders (id UUID PRIMARY KEY, data JSONB)
Indexación requerida: PK en id, B-Tree sobre timestamp extraído de JSONB
"""

import os
import sys
import io
import json
import time
import psycopg2
from psycopg2 import extras

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATASET_FILE = os.path.join("dataset", "orders_500k.jsonl")
PG_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "user": "benchmark",
    "password": "benchmark",
    "dbname": "benchmark_db"
}
BATCH_SIZE = 10000

def main():
    if not os.path.exists(DATASET_FILE):
        print(f"[!] Error: No se encontro el archivo {DATASET_FILE}")
        sys.exit(1)

    print("==================================================")
    print("[*] Iniciando carga masiva en PostgreSQL (JSONB)...")
    print(f"[*] Destino: localhost:{PG_CONFIG['port']} -> {PG_CONFIG['dbname']}.orders")
    print("==================================================")

    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    # 1. Preparar tabla limpia
    print("[*] Recreando tabla 'orders'...")
    cur.execute("DROP TABLE IF EXISTS orders CASCADE;")
    cur.execute("""
        CREATE TABLE orders (
            id UUID PRIMARY KEY,
            data JSONB NOT NULL
        );
    """)

    # 2. Carga masiva optimizada usando COPY en memoria (streaming buffers)
    print("[*] Insertando 500,000 registros mediante COPY binario/texto...")
    inicio = time.time()
    insertados = 0
    buffer = io.StringIO()

    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        for line in f:
            doc = json.loads(line)
            order_id = doc["order_id"]
            # Escapar barras y saltos si los hubiera para formato COPY
            data_json = json.dumps(doc).replace("\\", "\\\\")
            buffer.write(f"{order_id}\t{data_json}\n")
            insertados += 1

            if insertados % BATCH_SIZE == 0:
                buffer.seek(0)
                cur.copy_from(buffer, "orders", columns=("id", "data"))
                buffer.close()
                buffer = io.StringIO()

                progreso = (insertados / 500000) * 100
                transcurrido = time.time() - inicio
                qps = insertados / transcurrido if transcurrido > 0 else 0
                print(f"[{progreso:5.1f}%] {insertados:,} registros copiados ({qps:,.0f} reg/s)")

        if buffer.tell() > 0:
            buffer.seek(0)
            cur.copy_from(buffer, "orders", columns=("id", "data"))
            buffer.close()

    tiempo_carga = time.time() - inicio
    print(f"\n[+] Ingesta de {insertados:,} registros completada en {tiempo_carga:.2f} segundos.")

    # 3. Creación de índices según especificación de la universidad:
    # "PK en id; B-Tree sobre timestamp extraído del JSONB"
    print("\n[*] Creando indices requeridos...")
    idx_inicio = time.time()

    print("  [*] Generando indice B-Tree sobre timestamp extraido del JSONB...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_timestamp ON orders (((data->>'timestamp')));
    """)
    tiempo_indices = time.time() - idx_inicio
    print(f"[+] Indice creado en {tiempo_indices:.2f} segundos.")

    # 4. Auditoría de conteo
    cur.execute("SELECT COUNT(*) FROM orders;")
    total_final = cur.fetchone()[0]
    print(f"\n[OK] Auditoria PostgreSQL: {total_final:,} registros listos en la tabla 'orders'.\n")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()

