#!/usr/bin/env python3
"""
Script de Carga Masiva e Indexación para MongoDB
Experimento IT2iD (2026)
Colección: orders (sin sharding)
Índices requeridos: timestamp y order_id
"""

import os
import sys
import json
import time
import pymongo

# Evitar problemas de codificación en consolas Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATASET_FILE = os.path.join("dataset", "orders_500k.jsonl")
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "benchmark_db"
COLL_NAME = "orders"
BATCH_SIZE = 5000

def main():
    if not os.path.exists(DATASET_FILE):
        print(f"[!] Error: No se encontro el archivo {DATASET_FILE}")
        sys.exit(1)

    print("==================================================")
    print("[*] Iniciando carga masiva en MongoDB...")
    print(f"[*] Destino: {MONGO_URI}{DB_NAME}.{COLL_NAME}")
    print("==================================================")

    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    coll = db[COLL_NAME]

    # Limpiar colección previa para garantizar estado limpio y reproducible
    coll.drop()
    print("[*] Coleccion previa limpiada.")

    inicio = time.time()
    batch = []
    insertados = 0

    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        for line in f:
            doc = json.loads(line)
            batch.append(doc)

            if len(batch) >= BATCH_SIZE:
                coll.insert_many(batch, ordered=False)
                insertados += len(batch)
                batch.clear()

                if insertados % 50000 == 0:
                    progreso = (insertados / 500000) * 100
                    transcurrido = time.time() - inicio
                    qps = insertados / transcurrido if transcurrido > 0 else 0
                    print(f"[{progreso:5.1f}%] {insertados:,} documentos insertados ({qps:,.0f} doc/s)")

        if batch:
            coll.insert_many(batch, ordered=False)
            insertados += len(batch)
            batch.clear()

    tiempo_carga = time.time() - inicio
    print(f"\n[+] Ingesta de {insertados:,} documentos completada en {tiempo_carga:.2f} segundos.")

    # Creación de índices según especificación de la universidad:
    # "Índice simple en timestamp y order_id"
    print("\n[*] Creando indices requeridos...")
    idx_inicio = time.time()
    
    coll.create_index([("timestamp", pymongo.ASCENDING)], name="idx_timestamp")
    print("  [+] Indice simple en 'timestamp' creado.")

    coll.create_index([("order_id", pymongo.ASCENDING)], name="idx_order_id")
    print("  [+] Indice simple en 'order_id' creado.")
    
    tiempo_indices = time.time() - idx_inicio
    print(f"[+] Indices creados en {tiempo_indices:.2f} segundos.")

    total_final = coll.count_documents({})
    print(f"\n[OK] Auditoria MongoDB: {total_final:,} documentos listos en la coleccion '{COLL_NAME}'.\n")

if __name__ == "__main__":
    main()

