# 02. Especificación del Dataset Sintético

## Parámetros Generales
* **Cantidad de registros:** 500,000 órdenes de compra.
* **Formato:** JSON / JSONL.
* **Nivel de anidamiento:** 3 niveles de profundidad jerárquica.
* **Promedio de ítems por registro:** 3 ítems en el arreglo de compra.
* **Distribución de generación:** de 1 a 5 ítems con pesos simétricos alrededor de 3; la auditoría exige un promedio observado dentro de ±0.01.

---

## Estructura de Atributos

```json
{
  "order_id": "UUID-v4",
  "timestamp": "2026-03-15T14:32:00Z (ISO-8601)",
  "customer": {
    "id": "CUST-XXXXXX",
    "tier": "gold | silver | bronze | standard",
    "segment": "enterprise | retail | small_business",
    "geo": {
      "country": "MX",
      "state": "Chiapas",
      "city": "Tuxtla Gutierrez",
      "zip": "29000",
      "coordinates": {
        "lat": 16.7569,
        "lng": -93.1292
      }
    }
  },
  "items": [
    {
      "sku": "PROD-101",
      "category": "Electronics",
      "brand": "TechCorp",
      "qty": 2,
      "price": 120.50,
      "tax_pct": 0.16,
      "discounts": 10.00
    }
  ],
  "payment": {
    "method": "credit_card | debit_card | paypal | transfer",
    "status": "completed | pending | failed",
    "transaction_id": "TXN-XXXXXXXX",
    "gateway_latency_ms": 145,
    "totals": {
      "subtotal": 231.00,
      "tax": 36.96,
      "discounts": 20.00,
      "final_total": 247.96
    },
    "final_total": 247.96
  },
  "metadata": {
    "channel": "web | mobile_app | pos | api",
    "user_agent": "Mozilla/5.0 ...",
    "session_id": "SESS-XXXXXXXX",
    "flags": {
      "is_fraud_check_passed": true,
      "priority_shipping": false
    }
  }
}
```
