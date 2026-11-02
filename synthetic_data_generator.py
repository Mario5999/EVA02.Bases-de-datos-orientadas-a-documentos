#!/usr/bin/env python3
"""
Generador de Dataset Sintético de 500,000 órdenes para Experimento IT2iD (2026).
Cumple con las especificaciones exactas:
- 500,000 registros
- Formato JSON / JSONL
- 3 niveles de anidamiento
- Promedio de 3 ítems por registro
- Campos: order_id (UUID), timestamp (ISO-8601), customer, items, payment, metadata.
"""

import os
import sys
import json
import uuid
import random
import time
from datetime import datetime, timedelta

# Configurar salida segura en consolas Windows (evitar problemas de cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Asegurar semilla para reproducibilidad si se desea, o usar aleatoriedad controlada
random.seed(42)

TOTAL_REGISTROS = 500_000
LOTE_ESCRITURA = 10_000
OUTPUT_DIR = "dataset"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "orders_500k.jsonl")

# Catálogos predefinidos para generación ultra-rápida
PAISES_GEO = [
    {"country": "MX", "state": "Chiapas", "city": "Tuxtla Gutierrez", "zip": "29000", "lat": 16.7569, "lng": -93.1292},
    {"country": "MX", "state": "Jalisco", "city": "Guadalajara", "zip": "44100", "lat": 20.6597, "lng": -103.3496},
    {"country": "MX", "state": "CDMX", "city": "Ciudad de Mexico", "zip": "01000", "lat": 19.4326, "lng": -99.1332},
    {"country": "MX", "state": "Nuevo Leon", "city": "Monterrey", "zip": "64000", "lat": 25.6866, "lng": -100.3161},
    {"country": "US", "state": "California", "city": "Los Angeles", "zip": "90001", "lat": 34.0522, "lng": -118.2437},
    {"country": "US", "state": "Texas", "city": "Austin", "zip": "73301", "lat": 30.2672, "lng": -97.7431},
    {"country": "ES", "state": "Madrid", "city": "Madrid", "zip": "28001", "lat": 40.4168, "lng": -3.7038},
    {"country": "ES", "state": "Catalunya", "city": "Barcelona", "zip": "08001", "lat": 41.3851, "lng": 2.1734},
    {"country": "CO", "state": "Bogota D.C.", "city": "Bogota", "zip": "110111", "lat": 4.7110, "lng": -74.0721},
    {"country": "AR", "state": "Buenos Aires", "city": "Buenos Aires", "zip": "C1002", "lat": -34.6037, "lng": -58.3816}
]

TIERS = ["gold", "silver", "bronze", "standard"]
SEGMENTS = ["enterprise", "retail", "small_business"]

CATEGORIAS = [
    "Electronics", "Home & Kitchen", "Computers", "Sports & Outdoors",
    "Clothing", "Books", "Automotive", "Health & Personal Care"
]

MARCAS = [
    "TechCorp", "ApexIndustries", "NovaGear", "GlobalCraft", 
    "PrimeGoods", "VortexSystems", "Starlight", "TitanWorks"
]

METODOS_PAGO = ["credit_card", "debit_card", "paypal", "wire_transfer"]
ESTADOS_PAGO = ["completed", "completed", "completed", "completed", "pending", "failed"] # 66% completed para Q2

CANALES = ["web", "mobile_app", "pos", "api"]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"
]

# Rango de fechas: desde 2025-06-01 hasta 2026-10-30 (cubriendo Q2 con timestamp >= 2026-01-01)
FECHA_INICIO = datetime(2025, 6, 1, 0, 0, 0)
RANGO_SEGUNDOS = int((datetime(2026, 10, 30, 23, 59, 59) - FECHA_INICIO).total_seconds())

def generar_orden(indice):
    # Nivel 1: Atributos raíz
    order_id = str(uuid.uuid4())
    segundos_aleatorios = random.randint(0, RANGO_SEGUNDOS)
    fecha_dt = FECHA_INICIO + timedelta(seconds=segundos_aleatorios)
    timestamp_iso = fecha_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Nivel 2: Customer (con geo anidado)
    geo_info = random.choice(PAISES_GEO)
    customer = {
        "id": f"CUST-{(indice % 80000) + 10000:06d}",
        "tier": random.choice(TIERS),
        "segment": random.choice(SEGMENTS),
        "geo": {
            "country": geo_info["country"],
            "state": geo_info["state"],
            "city": geo_info["city"],
            "zip": geo_info["zip"],
            "coordinates": {
                "lat": round(geo_info["lat"] + random.uniform(-0.05, 0.05), 4),
                "lng": round(geo_info["lng"] + random.uniform(-0.05, 0.05), 4)
            }
        }
    }

    # Nivel 2: Items (arreglo con promedio de 3 ítems: distribución [1, 2, 3, 4, 5])
    num_items = random.choices([1, 2, 3, 4, 5], weights=[0.10, 0.20, 0.40, 0.20, 0.10], k=1)[0]
    items = []
    subtotal = 0.0

    for i in range(num_items):
        qty = random.randint(1, 4)
        # Precios entre 10 y 250 (garantizando precios mayores y menores a 50 para el filtro de Q1)
        price = round(random.uniform(10.0, 250.0), 2)
        tax_pct = 0.16
        discounts = round(random.choice([0.0, 5.0, 10.0, 15.0]), 2)
        
        item = {
            "sku": f"SKU-{random.randint(100, 999):03d}",
            "category": random.choice(CATEGORIAS),
            "brand": random.choice(MARCAS),
            "qty": qty,
            "price": price,
            "tax_pct": tax_pct,
            "discounts": discounts
        }
        items.append(item)
        subtotal += round(qty * price, 2)

    subtotal = round(subtotal, 2)
    tax_total = round(subtotal * 0.16, 2)
    total_descuentos = round(sum(it["discounts"] for it in items), 2)
    final_total = max(round(subtotal + tax_total - total_descuentos, 2), 1.0)

    # Nivel 2: Payment (con totals y final_total)
    payment_status = random.choice(ESTADOS_PAGO)
    payment = {
        "method": random.choice(METODOS_PAGO),
        "status": payment_status,
        "transaction_id": f"TXN-{uuid.uuid4().hex[:12].upper()}",
        "gateway_latency_ms": random.randint(45, 450),
        "totals": {
            "subtotal": subtotal,
            "tax": tax_total,
            "discounts": total_descuentos,
            "final_total": final_total
        },
        "final_total": final_total
    }

    # Nivel 2: Metadata
    metadata = {
        "channel": random.choice(CANALES),
        "user_agent": random.choice(USER_AGENTS),
        "session_id": f"SESS-{uuid.uuid4().hex[:16]}",
        "flags": {
            "is_fraud_check_passed": random.random() > 0.02,
            "priority_shipping": random.choice([True, False])
        }
    }

    # Documento completo JSON de 3 niveles
    return {
        "order_id": order_id,
        "timestamp": timestamp_iso,
        "customer": customer,
        "items": items,
        "payment": payment,
        "metadata": metadata
    }

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"==================================================")
    print(f"[*] Iniciando generacion de {TOTAL_REGISTROS:,} ordenes sinteticas")
    print(f"[*] Destino: {OUTPUT_FILE}")
    print(f"==================================================")

    inicio = time.time()
    lote = []
    escritos = 0

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for idx in range(1, TOTAL_REGISTROS + 1):
            doc = generar_orden(idx)
            lote.append(json.dumps(doc, ensure_ascii=False) + "\n")

            if len(lote) >= LOTE_ESCRITURA:
                f.writelines(lote)
                escritos += len(lote)
                lote.clear()

                if escritos % 50_000 == 0:
                    progreso = (escritos / TOTAL_REGISTROS) * 100
                    transcurrido = time.time() - inicio
                    qps = escritos / transcurrido if transcurrido > 0 else 0
                    print(f"[{progreso:5.1f}%] {escritos:,} registros generados ({qps:,.0f} reg/s)")

        # Escribir registros remanentes si hubiera
        if lote:
            f.writelines(lote)
            escritos += len(lote)
            lote.clear()

    total_tiempo = time.time() - inicio
    tamano_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)

    print(f"\n[+] Generacion completada con exito!")
    print(f"[*] Registros totales: {escritos:,}")
    print(f"[*] Tamano de archivo: {tamano_mb:.2f} MB")
    print(f"[*] Tiempo total: {total_tiempo:.2f} segundos")
    print(f"[*] Velocidad promedio: {escritos / total_tiempo:,.0f} registros/segundo\n")

if __name__ == "__main__":
    main()
