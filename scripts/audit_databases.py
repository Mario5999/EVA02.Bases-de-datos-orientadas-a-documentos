#!/usr/bin/env python3
"""
Auditoría de consistencia de bases de datos
Verifica que ambas bases tengan exactamente 500,000 registros y los índices exigidos por el documento.
"""

import sys
import pymongo
import psycopg2

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def main():
    print("==================================================")
    print("[*] AUDITORIA DE FASE 4: INGESTA E INDEXACION")
    print("==================================================")

    # 1. Auditar MongoDB
    mc = pymongo.MongoClient("mongodb://localhost:27017/")
    m_coll = mc["benchmark_db"]["orders"]
    m_count = m_coll.count_documents({})
    m_indexes = [idx["name"] for idx in m_coll.list_indexes()]
    m_item_stats = list(m_coll.aggregate([
        {"$project": {"item_count": {"$size": "$items"}}},
        {"$group": {"_id": None, "average": {"$avg": "$item_count"}}}
    ]))
    m_average_items = float(m_item_stats[0]["average"]) if m_item_stats else 0.0

    print(f"MongoDB ('orders'):")
    print(f"  * Registros totales: {m_count:,}")
    print(f"  * Promedio de items por orden: {m_average_items:.4f}")
    print(f"  * Indices presentes: {m_indexes}")

    # 2. Auditar PostgreSQL
    pg = psycopg2.connect(
        host="localhost", port=5433, user="benchmark", password="benchmark", dbname="benchmark_db"
    )
    cur = pg.cursor()
    cur.execute("SELECT COUNT(*) FROM orders;")
    p_count = cur.fetchone()[0]

    cur.execute("SELECT AVG(jsonb_array_length(data->'items')) FROM orders;")
    p_average_items = float(cur.fetchone()[0] or 0.0)

    cur.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'orders';")
    p_indexes = [row[0] for row in cur.fetchall()]

    print(f"\nPostgreSQL ('orders'):")
    print(f"  * Registros totales: {p_count:,}")
    print(f"  * Promedio de items por orden: {p_average_items:.4f}")
    print(f"  * Indices presentes: {p_indexes}")

    cur.close()
    pg.close()

    # Validaciones obligatorias
    assert m_count == 500000, f"Error: MongoDB tiene {m_count} registros en vez de 500,000"
    assert p_count == 500000, f"Error: PostgreSQL tiene {p_count} registros en vez de 500,000"
    assert abs(m_average_items - 3.0) < 0.01, (
        f"Error: MongoDB tiene promedio {m_average_items:.4f} items; regenere y recargue el dataset"
    )
    assert abs(p_average_items - 3.0) < 0.01, (
        f"Error: PostgreSQL tiene promedio {p_average_items:.4f} items; regenere y recargue el dataset"
    )
    assert "idx_timestamp" in m_indexes, "Falta índice de timestamp en MongoDB"
    assert "idx_order_id" in m_indexes, "Falta índice de order_id en MongoDB"
    assert "orders_pkey" in p_indexes, "Falta PK en PostgreSQL"
    assert "idx_orders_timestamp" in p_indexes, "Falta índice de timestamp en PostgreSQL"

    print("\n==================================================")
    print("✅ AUDITORIA 100% EXITOSA:")
    print("   Ambos motores tienen exactamente 500,000 registros.")
    print("   Todos los índices exigidos están creados y activos.")
    print("==================================================\n")

if __name__ == "__main__":
    main()
