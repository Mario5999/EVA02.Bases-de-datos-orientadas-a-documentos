/**
 * CONSULTA Q1: Unwind, Filter & Grouping (Saturación de CPU)
 * Experimento IT2iD (2026) - MongoDB Pipeline
 * 
 * Objetivo: Desanidar el arreglo de ítems, filtrar price > 50,
 * calcular subtotal (qty * price) y agrupar sumatoria y promedio por país y categoría.
 */

db.orders.aggregate([
  { 
    "$unwind": "$items" 
  },
  { 
    "$match": { 
      "items.price": { "$gt": 50 } 
    } 
  },
  {
    "$group": {
      "_id": {
        "country": "$customer.geo.country",
        "category": "$items.category"
      },
      "total_revenue": { 
        "$sum": { "$multiply": ["$items.qty", "$items.price"] } 
      },
      "avg_revenue": { 
        "$avg": { "$multiply": ["$items.qty", "$items.price"] } 
      },
      "count": { 
        "$sum": 1 
      }
    }
  }
]);

