/**
 * CONSULTA Q2: Massive Sort & Top-K (Estrés de Buffer de Memoria)
 * Experimento IT2iD (2026) - MongoDB Pipeline
 * 
 * Objetivo: Filtrar órdenes completadas con timestamp >= 2026-01-01,
 * ordenar descendentemente por payment.final_total y obtener Top-1000.
 * 
 * Variantes de estrés de memoria:
 * - allowDiskUse: false (debe fallar si el buffer de ordenamiento excede 100MB de RAM)
 * - allowDiskUse: true  (permite volcado temporal a disco)
 */

db.orders.aggregate([
  { 
    "$match": {
      "payment.status": "completed",
      "timestamp": { "$gte": "2026-01-01T00:00:00Z" }
    } 
  },
  { 
    "$sort": { "payment.final_total": -1 } 
  },
  { 
    "$limit": 1000 
  },
  { 
    "$project": {
      "order_id": 1, 
      "customer.id": 1, 
      "payment.final_total": 1
    } 
  }
], {
  allowDiskUse: false // o true según la variante evaluada
});

