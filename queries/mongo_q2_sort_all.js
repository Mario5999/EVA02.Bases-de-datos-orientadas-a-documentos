/**
 * Q2_SORT_ALL: full sort workload to expose memory pressure and disk spill.
 * Kept separate from the original Top-1000 query so its semantics remain intact.
 */
db.orders.aggregate([
  {
    "$match": {
      "payment.status": "completed",
      "timestamp": { "$gte": "2026-01-01T00:00:00Z" }
    }
  },
  {
    "$setWindowFields": {
      "sortBy": { "payment.final_total": -1 },
      "output": { "rank": { "$documentNumber": {} } }
    }
  },
  {
    "$group": {
      "_id": null,
      "count": { "$sum": 1 },
      "rank_sum": { "$sum": "$rank" },
      "highest_total": { "$max": "$payment.final_total" },
      "lowest_total": { "$min": "$payment.final_total" }
    }
  }
], {
  allowDiskUse: true // Cambiar a false para medir el límite de memoria.
});
