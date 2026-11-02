#!/usr/bin/env python3
"""
Módulo Recolector de Métricas de Hardware y Telemetría
Consulta la API HTTP de Prometheus para cAdvisor y cgroups v2
Experimento IT2iD (2026)
"""

import sys
import requests

PROMETHEUS_URL = "http://localhost:9090"

class PrometheusMetricError(RuntimeError):
    """Raised when a required Prometheus metric cannot be read."""

def _query_prometheus(query: str) -> list:
    """Ejecuta una consulta instantánea en la API de Prometheus."""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise PrometheusMetricError(f"Prometheus request failed for {query!r}: {exc}") from exc
    except ValueError as exc:
        raise PrometheusMetricError("Prometheus returned invalid JSON") from exc

    if data.get("status") != "success":
        raise PrometheusMetricError(
            f"Prometheus query failed for {query!r}: {data.get('error', 'unknown error')}"
        )
    results = data.get("data", {}).get("result", [])
    if not results:
        raise PrometheusMetricError(f"Prometheus returned no series for {query!r}")
    return results

def _query_value(query: str) -> float:
    results = _query_prometheus(query)
    try:
        value = float(results[0]["value"][1])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise PrometheusMetricError(f"Prometheus returned an invalid value for {query!r}") from exc
    return value

def get_cpu_throttled_seconds(container_name: str) -> float:
    """
    Obtiene los segundos acumulados de CPU Throttled para el contenedor.
    KPI: container_cpu_cfs_throttled_seconds_total
    """
    # cAdvisor reporta con nombre que contiene el container_name
    query = f'sum(container_cpu_cfs_throttled_seconds_total{{name=~".*{container_name}.*"}})'
    val = _query_value(query)
    return round(val, 4)

def get_memory_rss_mb(container_name: str) -> float:
    """
    Obtiene la memoria física residente (RSS) en Megabytes.
    KPI: container_memory_rss_bytes
    """
    query = f'max(container_memory_rss{{name=~".*{container_name}.*"}})'
    val_bytes = _query_value(query)
    return round(val_bytes / (1024 * 1024), 2)

def get_oom_events(container_name: str) -> float:
    """
    Verifica si el contenedor sufrió un evento OOM (Out Of Memory).
    KPI: oom_killed
    """
    query = f'sum(container_oom_events_total{{name=~".*{container_name}.*"}})'
    return _query_value(query)

def get_max_memory_rss_mb(container_name: str, start: float, end: float) -> float:
    """Obtiene el máximo RSS observado durante el intervalo de medición."""
    query = f'max(container_memory_rss{{name=~".*{container_name}.*"}})'
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params={"query": query, "start": start, "end": end, "step": "1s"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise PrometheusMetricError(f"Prometheus range query failed: {exc}") from exc
    except ValueError as exc:
        raise PrometheusMetricError("Prometheus returned invalid JSON") from exc

    if data.get("status") != "success":
        raise PrometheusMetricError(
            f"Prometheus range query failed: {data.get('error', 'unknown error')}"
        )
    results = data.get("data", {}).get("result", [])
    values = [
        float(value)
        for series in results
        for _, value in series.get("values", [])
    ]
    if not values:
        raise PrometheusMetricError(
            f"Prometheus returned no RSS samples for {container_name!r}"
        )
    return round(max(values) / (1024 * 1024), 2)

def snapshot_metrics(container_name: str):
    """Toma una foto de telemetría completa de un contenedor."""
    return {
        "throttled_seconds": get_cpu_throttled_seconds(container_name),
        "rss_mb": get_memory_rss_mb(container_name),
        "oom_events": get_oom_events(container_name)
    }

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Probando recolección de métricas desde Prometheus:")
    for c in ["mongodb", "postgres"]:
        metrics = snapshot_metrics(c)
        print(f"[{c}] Throttled: {metrics['throttled_seconds']}s | RSS: {metrics['rss_mb']} MB | OOM events: {metrics['oom_events']}")
