#!/usr/bin/env python3
"""Analyze the official benchmark CSV and generate reproducible report artifacts."""

from __future__ import annotations

import argparse
import itertools
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import requests

ENGINES = ("mongodb", "postgresql")
PROFILES = ("PROFILE_A_BASELINE", "PROFILE_B_MEDIUM", "PROFILE_C_SEVERE")
QUERIES = ("q1", "q2")
CONCURRENCIES = (1, 10, 50)
REPETITIONS = (1, 2, 3)
KEY_COLUMNS = ["engine", "profile", "query_id", "concurrency", "run_number"]
METRICS = [
    "throughput_qps",
    "latency_p50_ms",
    "latency_p95_ms",
    "latency_p99_ms",
    "cpu_throttled_seconds",
    "max_rss_mb",
]
EXPECTED_COLUMNS = [
    "timestamp_epoch",
    *KEY_COLUMNS,
    *METRICS,
    "disk_spill",
    "status",
]


def parse_bool(value: Any) -> bool | None:
    if pd.isna(value):
        return None
    normalized = str(value).strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    return None


def expected_keys() -> set[tuple[Any, ...]]:
    return set(
        itertools.product(
            ENGINES, PROFILES, QUERIES, CONCURRENCIES, REPETITIONS
        )
    )


def load_results(csv_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, set]:
    raw = pd.read_csv(csv_path)
    if list(raw.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            f"CSV header mismatch: expected {EXPECTED_COLUMNS}, got {list(raw.columns)}"
        )

    for column in ["timestamp_epoch", "concurrency", "run_number", *METRICS]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    raw["disk_spill"] = raw["disk_spill"].map(parse_bool)

    success = raw.loc[raw["status"].eq("SUCCESS")].copy()
    success = success.sort_values("timestamp_epoch").drop_duplicates(
        KEY_COLUMNS, keep="last"
    )
    success_keys = set(
        success[KEY_COLUMNS].itertuples(index=False, name=None)
    )
    missing_keys = expected_keys() - success_keys
    return raw, success, missing_keys


def summarize_cells(success: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dimensions = ["engine", "profile", "query_id", "concurrency"]
    for key in itertools.product(ENGINES, PROFILES, QUERIES, CONCURRENCIES):
        group = success.loc[
            success[dimensions].eq(pd.Series(key, index=dimensions)).all(axis=1)
        ]
        row = dict(zip(dimensions, key))
        row["successful_repetitions"] = group["run_number"].nunique()
        row["expected_repetitions"] = len(REPETITIONS)
        row["complete"] = row["successful_repetitions"] == len(REPETITIONS)
        for metric in METRICS:
            row[f"median_{metric}"] = group[metric].median()
        row["spill_true_repetitions"] = int(group["disk_spill"].eq(True).sum())
        rows.append(row)

    columns = [
        "engine",
        "profile",
        "query_id",
        "concurrency",
        "successful_repetitions",
        "expected_repetitions",
        "complete",
        *[f"median_{metric}" for metric in METRICS],
        "spill_true_repetitions",
    ]
    return pd.DataFrame(rows, columns=columns)


def summarize_engine_query(success: pd.DataFrame) -> pd.DataFrame:
    expected_per_group = len(PROFILES) * len(CONCURRENCIES) * len(REPETITIONS)
    rows = []
    for (engine, query), group in success.groupby(["engine", "query_id"], sort=True):
        row = {
            "engine": engine,
            "query_id": query,
            "successful_runs": len(group),
            "expected_runs": expected_per_group,
        }
        for metric in METRICS:
            row[f"median_{metric}"] = group[metric].median()
        row["spill_true_runs"] = int(group["disk_spill"].eq(True).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def format_value(value: Any, digits: int = 2) -> str:
    if pd.isna(value):
        return "—"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return f"{value:.{digits}f}" if isinstance(value, (int, float)) else str(value)


def markdown_table(frame: pd.DataFrame, columns: list[str], headers: list[str]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    integer_headers = {"SUCCESS", "Esperadas", "Corridas con spill"}
    for _, row in frame[columns].iterrows():
        lines.append(
            "| "
            + " | ".join(
                f"{int(value)}" if header in integer_headers and not pd.isna(value)
                else format_value(value)
                for header, value in zip(headers, row.tolist())
            )
            + " |"
        )
    return "\n".join(lines)


def plot_latency(cells: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharex=True)
    colors = {"mongodb": "#2878B5", "postgresql": "#E87500"}
    for row_index, query in enumerate(QUERIES):
        for col_index, profile in enumerate(PROFILES):
            ax = axes[row_index, col_index]
            subset = cells.loc[
                cells["query_id"].eq(query) & cells["profile"].eq(profile)
            ]
            for engine in ENGINES:
                engine_data = subset.loc[subset["engine"].eq(engine)].sort_values(
                    "concurrency"
                )
                ax.plot(
                    engine_data["concurrency"],
                    engine_data["median_latency_p99_ms"],
                    marker="o",
                    linewidth=1.8,
                    color=colors[engine],
                    label=engine,
                )
                for _, point in engine_data.iterrows():
                    ax.annotate(
                        f'{int(point["successful_repetitions"])}/3',
                        (point["concurrency"], point["median_latency_p99_ms"]),
                        xytext=(4, 5),
                        textcoords="offset points",
                        fontsize=7,
                        color=colors[engine],
                    )
                missing = sorted(
                    engine_data.loc[
                        engine_data["successful_repetitions"].eq(0),
                        "concurrency",
                    ].tolist()
                )
                if missing:
                    ax.text(
                        0.98,
                        0.04 if engine == "mongodb" else 0.12,
                        f'{engine}: sin SUCCESS en c={",".join(map(str, missing))}',
                        transform=ax.transAxes,
                        ha="right",
                        fontsize=7,
                        color=colors[engine],
                    )
            ax.set_title(f"{query.upper()} · {profile.replace('PROFILE_', '')}")
            ax.set_xticks(CONCURRENCIES)
            ax.grid(True, alpha=0.25)
            if col_index == 0:
                ax.set_ylabel("Latencia P99 mediana (ms)")
            if row_index == 1:
                ax.set_xlabel("Concurrencia")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.04),
        ncol=2,
        frameon=False,
    )
    fig.suptitle(
        "Latencia P99 por concurrencia\nEtiquetas: repeticiones SUCCESS / 3",
        y=1.16,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)


def plot_throttling(success: pd.DataFrame, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    engine_colors = {"mongodb": "#2878B5", "postgresql": "#E87500"}
    profile_markers = {
        "PROFILE_A_BASELINE": "o",
        "PROFILE_B_MEDIUM": "s",
        "PROFILE_C_SEVERE": "^",
    }
    for engine in ENGINES:
        for profile in PROFILES:
            for query in QUERIES:
                points = success.loc[
                    success["engine"].eq(engine)
                    & success["profile"].eq(profile)
                    & success["query_id"].eq(query)
                ]
                if points.empty:
                    continue
                ax.scatter(
                    points["cpu_throttled_seconds"],
                    points["throughput_qps"],
                    color=engine_colors[engine],
                    marker=profile_markers[profile],
                    facecolors=(
                        engine_colors[engine] if query == "q1" else "white"
                    ),
                    edgecolors=engine_colors[engine],
                    alpha=0.78,
                    s=48,
                )

    from matplotlib.lines import Line2D

    legend_items = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=engine_colors[e],
               markeredgecolor=engine_colors[e], label=e, markersize=8)
        for e in ENGINES
    ]
    legend_items.extend(
        Line2D([0], [0], marker=marker, color="#555555", linestyle="None",
               label=profile.replace("PROFILE_", ""), markersize=8)
        for profile, marker in profile_markers.items()
    )
    legend_items.extend(
        [
            Line2D([0], [0], marker="o", color="#555555", markerfacecolor="#555555",
                   linestyle="None", label="Q1", markersize=7),
            Line2D([0], [0], marker="o", color="#555555", markerfacecolor="white",
                   linestyle="None", label="Q2", markersize=7),
        ]
    )
    ax.legend(handles=legend_items, ncol=3, loc="best", frameon=True)
    ax.set_xlabel("CPU throttling acumulado en medición (s)")
    ax.set_ylabel("Throughput (QPS)")
    ax.set_title("CPU throttling frente a throughput (solo corridas SUCCESS)")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fetch_rss_history(
    success: pd.DataFrame, prometheus_url: str, step_seconds: int
) -> tuple[dict[str, list[tuple[float, float]]], str | None]:
    if success.empty:
        return {}, "No hay corridas SUCCESS para delimitar el intervalo de telemetría."
    start = int(success["timestamp_epoch"].min())
    longest_tail_seconds = max(600, int(success["latency_p99_ms"].max() / 1000) + 60)
    end = int(success["timestamp_epoch"].max()) + longest_tail_seconds
    history: dict[str, list[tuple[float, float]]] = {}
    try:
        for engine, container in (
            ("mongodb", "it2id_mongodb"),
            ("postgresql", "it2id_postgres"),
        ):
            query = f'max(container_memory_rss{{name="{container}"}})'
            response = requests.get(
                f"{prometheus_url.rstrip('/')}/api/v1/query_range",
                params={
                    "query": query,
                    "start": start,
                    "end": end,
                    "step": f"{step_seconds}s",
                },
                timeout=90,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") != "success":
                raise RuntimeError(payload.get("error", "Prometheus query failed"))
            values = [
                (float(timestamp), float(value) / (1024 * 1024))
                for series in payload.get("data", {}).get("result", [])
                for timestamp, value in series.get("values", [])
            ]
            if values:
                history[engine] = values
        if not history:
            return {}, "Prometheus no devolvió muestras RSS en el intervalo solicitado."
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        return {}, f"No se pudo consultar la historia de Prometheus: {exc}"
    return history, None


def plot_rss(
    success: pd.DataFrame,
    history: dict[str, list[tuple[float, float]]],
    warning: str | None,
    output: Path,
    step_seconds: int,
) -> str:
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = {"mongodb": "#2878B5", "postgresql": "#E87500"}
    if history:
        for engine, values in history.items():
            timestamps = [datetime.fromtimestamp(ts) for ts, _ in values]
            rss = [value for _, value in values]
            ax.plot(timestamps, rss, linewidth=0.8, alpha=0.8, color=colors[engine], label=engine)
        method = f"Historia RSS de Prometheus (máximo por contenedor, muestras cada {step_seconds} s)"
    else:
        for engine in ENGINES:
            points = success.loc[success["engine"].eq(engine)].sort_values(
                "timestamp_epoch"
            )
            if points.empty:
                continue
            times = points["timestamp_epoch"].map(datetime.fromtimestamp)
            ax.plot(
                times,
                points["max_rss_mb"],
                marker=".",
                linewidth=0.8,
                alpha=0.75,
                color=colors[engine],
                label=engine,
            )
        method = "RSS máximo por corrida del CSV (no es una curva de muestreo continuo)"
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    fig.autofmt_xdate()
    ax.set_ylabel("RSS (MiB)")
    ax.set_xlabel("Hora local")
    ax.set_title("Memoria residente durante la ventana del experimento")
    ax.grid(True, alpha=0.25)
    ax.legend()
    if warning:
        ax.text(
            0.01,
            0.02,
            warning,
            transform=ax.transAxes,
            fontsize=8,
            wrap=True,
            color="#8b0000",
        )
    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return method


def unresolved_rows(missing_keys: set) -> list[tuple[Any, ...]]:
    return sorted(missing_keys, key=lambda row: (row[0], row[1], row[2], row[3], row[4]))


def create_report(
    raw: pd.DataFrame,
    success: pd.DataFrame,
    missing_keys: set,
    cells: pd.DataFrame,
    engine_query: pd.DataFrame,
    rss_method: str,
    report_path: Path,
) -> None:
    all_cells = len(PROFILES) * len(QUERIES) * len(CONCURRENCIES)
    paired_complete = 0
    for profile, query, concurrency in itertools.product(
        PROFILES, QUERIES, CONCURRENCIES
    ):
        pair = cells.loc[
            cells["profile"].eq(profile)
            & cells["query_id"].eq(query)
            & cells["concurrency"].eq(concurrency)
        ]
        if len(pair) == 2 and pair["complete"].all():
            paired_complete += 1

    summary = markdown_table(
        engine_query,
        [
            "engine",
            "query_id",
            "successful_runs",
            "expected_runs",
            "median_throughput_qps",
            "median_latency_p95_ms",
            "median_latency_p99_ms",
            "median_cpu_throttled_seconds",
            "median_max_rss_mb",
            "spill_true_runs",
        ],
        [
            "Motor",
            "Query",
            "SUCCESS",
            "Esperadas",
            "QPS mediana",
            "P95 mediana (ms)",
            "P99 mediana (ms)",
            "Throttling mediano (s)",
            "RSS máximo mediano (MiB)",
            "Corridas con spill",
        ],
    )
    unresolved = "\n".join(
        f"- `{engine} / {profile} / {query.upper()} / concurrencia {concurrency} / repetición {run}`"
        for engine, profile, query, concurrency, run in unresolved_rows(missing_keys)
    )
    aborted_attempts = int(raw["status"].eq("ABORTED").sum())
    other_failed_attempts = int(
        (~raw["status"].isin(["SUCCESS", "ABORTED"])).sum()
    )
    report = f"""# Reporte técnico de métricas (análisis parcial)

## Alcance y estado

La matriz aprobada del playbook tiene 108 claves (2 motores × 3 perfiles × Q1/Q2 × concurrencias 1/10/50 × 3 repeticiones). Este análisis usa únicamente las filas `SUCCESS`, deduplicadas por clave; conserva los resultados fallidos para contabilizar y documentar las incidencias. No se considera que la matriz esté completa ni se hace una conclusión estadística definitiva.

- Claves esperadas: 108.
- Claves con al menos un resultado `SUCCESS`: {len(success)}.
- Claves sin resultado `SUCCESS`: {len(missing_keys)}.
- Filas de intentos en el CSV: {len(raw)} ({int(raw["status"].eq("SUCCESS").sum())} `SUCCESS`, {aborted_attempts} `ABORTED`, {other_failed_attempts} otros estados fallidos).
- Ventana de pared registrada: aproximadamente 15 h 44 min desde el primer aborto de arranque hasta el cierre del log; incluye recreaciones, esperas, abortos y reanudaciones, no solo medición.
- Celdas comparables completas (ambos motores, tres repeticiones por celda): {paired_complete}/{all_cells}.
- Fuente: [`mediciones.csv`](../mediciones.csv). Resúmenes reproducibles: [`resumen_por_celda.csv`](resumen_por_celda.csv) y [`resumen_por_motor_query.csv`](resumen_por_motor_query.csv).

## 1. Especificaciones del host y entorno Docker

Según la auditoría documentada, el host es Windows con backend WSL2 x86_64; Docker dispone de 8 CPU y 5.635 GiB, con cgroups v2. Los perfiles de contenedor son A (4 CPU/4096 MiB), B (2 CPU/2048 MiB) y C (1 CPU/1024 MiB), con swap igual al límite de memoria. Los motores son MongoDB y PostgreSQL 16; Prometheus, cAdvisor y Node Exporter recolectan telemetría. La matriz encontró una limitación práctica de memoria compartida de PostgreSQL, descrita en la sección 6.

## 2. Método de medición y baseline

Cada corrida usa 60 s de warmup, 300 s de medición y 60 s de cooldown; se limpia la caché entre escenarios. Q1 evalúa expansión/filtrado/agrupación; Q2 devuelve Top-1000. La configuración fija de Q2 es MongoDB `allowDiskUse=false` y PostgreSQL `work_mem=4MB`. Los valores consolidados son medianas de repeticiones exitosas; no se imputan los intentos fallidos ni se mezclan variantes preparatorias. El baseline es el perfil A (4 CPU/4 GiB). No se calcula significancia estadística con tres repeticiones y datos faltantes.

El límite de medición detiene la admisión de consultas después de 300 s, pero el runner espera a que terminen las consultas en curso antes de calcular los KPIs. Por ello, algunas latencias de cola superan los 300 s nominales; las tres repeticiones MongoDB/Q2/perfil C/concurrencia 50 reportaron P99 entre 481.17 y 515.10 s. El throughput usa el tiempo transcurrido hasta completar esos trabajadores, según el runner.

## 3. Resultados consolidados

Las siguientes medianas agrupan las corridas `SUCCESS` de cada motor y query a través de perfiles y concurrencias; `SUCCESS/Esperadas` hace visible la cobertura. Son descriptivas y no deben interpretarse como una comparación balanceada cuando el conteo sea menor al esperado.

{summary}

Los valores por perfil, concurrencia y repetición están disponibles en `resumen_por_celda.csv`; se recomienda usar esa tabla para interpretaciones condicionadas por la carga, no solo el agregado anterior.

## 4. Análisis gráfico

- [Latencia P99 vs concurrencia](graficas/latencia_p99_concurrencia.png): mediana por celda, separada por query y perfil; cada punto indica las repeticiones válidas de tres.
- [CPU throttling vs throughput](graficas/throttling_vs_throughput.png): una observación por corrida exitosa.
- [RSS a lo largo del experimento](graficas/rss_tiempo.png): {rss_method}.

## 5. Comparación de planes de ejecución

Los planes guardados en [`Contexto/09_planes_de_ejecucion_explain.md`](../Contexto/09_planes_de_ejecucion_explain.md) son evidencias de `EXPLAIN`/`executionStats` tomadas en la fase preparatoria, no mediciones de ejecución individuales de las 108 corridas.

- **Q1 en MongoDB:** `COLLSCAN`, 500,000 documentos examinados; el explain almacenado informa aproximadamente 2,571 ms. El pipeline expande `items` y agrupa resultados.
- **Q1 en PostgreSQL:** `Parallel Seq Scan` sobre 500,000 filas, expansión con `jsonb_array_elements` y `GroupAggregate`; costo estimado raíz 381,080.71..3,267,845.83. El plan reporta 14,550 buffers shared hit, 84,544 read, 220,386 temp read y 220,638 temp written (bloques), ordenamiento `external merge` y 7,024 ms de ejecución.
- **Q2 Top-1000 en MongoDB:** plan con `IXSCAN` del índice `timestamp`, `FETCH` por estado y `SORT` con límite 1000; `executionStats` reporta 293,342 claves/documentos examinados y aproximadamente 903 ms. MongoDB no expone en este explain un estimador de costo directamente comparable con el costo del planificador PostgreSQL ni contadores shared/temp buffers equivalentes.
- **Q2 Top-1000 en PostgreSQL:** costo estimado raíz 105,729.65..105,810.62; `Parallel Seq Scan`, buffers shared hit=14,644/read=84,448 y ordenamiento Top-N (`top-N heapsort`) en alrededor de 273 kB por worker, sin spill temporal en este plan. Ejecución: 299 ms con `work_mem=4MB`. `work_mem=64MB` y Q2_SORT_ALL son evidencia auxiliar, no parte de la matriz oficial.

Las duraciones EXPLAIN corresponden a una ejecución de plan con su propio estado de caché y no son directamente equivalentes al throughput concurrente del benchmark.

## 6. Memoria, spill y throttling

La incidencia principal fue PostgreSQL Q1 a concurrencia 50: el contenedor no pudo ampliar un segmento de memoria compartida de 1 MiB y reportó `No space left on device`. El error apareció durante warmup o medición bajo el `/dev/shm` predeterminado; afectó las tres repeticiones en los perfiles A/B/C. Nueve claves quedaron sin un resultado `SUCCESS`: ocho con último intento `ABORTED` y una con `PARTIAL_FAILURE`. La fila abortada temprana de MongoDB Q1/repetición 1 tiene una fila `SUCCESS` posterior y por ello esa clave sí cuenta como exitosa. No se aumentó `shm_size`, no se reintentaron las nueve claves y no se cambió la configuración aprobada.

Las tres corridas MongoDB/Q2/perfil C/concurrencia 50 tuvieron P99 mayor a la ventana nominal de 300 s; el runner esperó la terminación de los trabajadores activos. Se conservan como resultados medidos, y su duración mayor debe tenerse en cuenta al interpretar throughput y latencias.

La columna `disk_spill` indica si se observó escritura temporal/spill durante la corrida; las tablas de resumen cuentan estos casos solo entre ejecuciones `SUCCESS`. El throttling y RSS son métricas observadas por el recolector; ausencia de throttling reportado no demuestra ausencia de presión de CPU. No se infieren mediciones para filas abortadas.

Claves incompletas:
{unresolved}

## 7. Recomendaciones técnicas

1. Tratar estas conclusiones como preliminares y declarar explícitamente que 9/108 claves carecen de resultado válido.
2. No usar PostgreSQL Q1/concurrencia 50 para una comparación directa con MongoDB hasta contar con mediciones válidas bajo un protocolo revisado.
3. Si se autoriza una repetición futura, registrar primero como nueva versión de protocolo el tamaño de `/dev/shm`, comprobarlo en el contenedor antes de la corrida y reejecutar todas las comparaciones afectadas de forma consistente; no sobrescribir el CSV actual.
4. Conservar el CSV, logs de ejecución/incidencias, configuración Compose, planes EXPLAIN y versiones de contenedores junto con cualquier entrega.
5. Evitar extrapolar resultados del host local a producción cloud; repetir bajo límites, almacenamiento, red y versión de motor equivalentes al destino.

## Artefactos y reproducibilidad

Ejecutar desde la raíz del proyecto:

```powershell
& .\\venv\\Scripts\\python.exe .\\analisis\\graficador.py
```

El script vuelve a generar los resúmenes y las gráficas. Consulta el historial RSS de Prometheus para el intervalo de la matriz; si la API ya no conserva esas muestras, genera una visualización alternativa de los máximos RSS por corrida registrados en el CSV e identifica expresamente esa limitación.
"""
    report_path.write_text(report, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "mediciones.csv",
    )
    parser.add_argument(
        "--prometheus-url", default="http://localhost:9090"
    )
    parser.add_argument("--prometheus-step", type=int, default=15)
    args = parser.parse_args()
    if args.prometheus_step < 1:
        parser.error("--prometheus-step must be positive")

    output_dir = Path(__file__).resolve().parent
    graph_dir = output_dir / "graficas"
    graph_dir.mkdir(parents=True, exist_ok=True)

    raw, success, missing_keys = load_results(args.csv)
    cells = summarize_cells(success)
    engine_query = summarize_engine_query(success)
    cells.to_csv(output_dir / "resumen_por_celda.csv", index=False)
    engine_query.to_csv(output_dir / "resumen_por_motor_query.csv", index=False)

    plot_latency(cells, graph_dir / "latencia_p99_concurrencia.png")
    plot_throttling(success, graph_dir / "throttling_vs_throughput.png")
    history, warning = fetch_rss_history(
        success, args.prometheus_url, args.prometheus_step
    )
    rss_method = plot_rss(
        success, history, warning, graph_dir / "rss_tiempo.png", args.prometheus_step
    )
    report_path = Path(__file__).resolve().parents[1] / "reporte_final_metricas.md"
    create_report(
        raw,
        success,
        missing_keys,
        cells,
        engine_query,
        rss_method,
        report_path,
    )

    print(f"CSV filas: {len(raw)}")
    print(f"Claves SUCCESS únicas: {len(success)} / {len(expected_keys())}")
    print(f"Claves incompletas: {len(missing_keys)}")
    print(f"Fuente de la gráfica RSS: {rss_method}")
    if warning:
        print(f"Advertencia RSS: {warning}")
    print(f"Reporte: {report_path}")
    print(f"Artefactos: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
