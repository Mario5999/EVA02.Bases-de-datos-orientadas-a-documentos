/**
 * Memoria de trabajo del Asistente Copilot para el experimento MongoDB vs. PostgreSQL JSONB.
 * Archivo independiente de index.js; conservar solicitudes, decisiones, acciones y estado.
 */

module.exports = {
  identidad: "Asistente de IA usando Copilot SDK en VS Code",
  ultimaActualizacion: new Date().toISOString(),

  objetivo: "Comparar MongoDB y PostgreSQL JSONB con un dataset común y cargas de trabajo equivalentes.",

  preferenciasYAcuerdosConElUsuario: [
    "Avanzar fase por fase y preguntar si cada fase está completa.",
    "Si una fase está pendiente, preguntar antes de realizar el trabajo necesario para completarla.",
    "No iniciar la matriz oficial de 108 corridas sin autorización explícita.",
    "El usuario inicialmente decidió esperar y posteriormente autorizó explícitamente la matriz oficial."
  ],

  estadoGeneral: {
    fases1a6: "COMPLETADAS",
    fase7: "EJECUCIÓN PARCIAL; 99 de 108 claves SUCCESS y 9 claves por resolver",
    fase8: "ANALISIS PARCIAL COMPLETADO; reporte y graficas generados con 99 claves SUCCESS",
    matrizIniciada: true,
    archivoResultadosCompleto: "mediciones.csv (108 claves representadas; resultados incompletos)",
    corridasPlaneadas: 108,
    corridasExitosasUnicas: 99,
    clavesPendientes: 9,
    filasAbortadas: 9,
    filasPartialFailure: 1,
    causaPrincipalPendientes: "PostgreSQL Q1 concurrencia 50: falta de espacio en /dev/shm; warmup o consulta incompletos.",
    celdas: 36,
    repeticionesPorCelda: 3,
    corridasPorMotor: 54,
    corridasPorPerfil: 36,
    duracionMinimaEstimada: "12 h 36 min",
    alcance: "Matriz oficial de sección 6: 2 motores × 3 perfiles × Q1/Q2 × 3 concurrencias × 3 repeticiones. Q2_SORT_ALL y variantes adicionales excluidas.",
    configuracionQ2: {
      mongodb: "allowDiskUse=false",
      postgresql: "work_mem=4MB"
    }
  },

  estadoPorFase: {
    fase1: {
      nombre: "Preparación del entorno y dependencias",
      estado: "COMPLETADA",
      detalle: "Herramientas, entorno virtual, paquetes y configuración base revisados."
    },
    fase2: {
      nombre: "Dataset sintético",
      estado: "COMPLETADA",
      detalle: "500,000 registros JSON válidos; 1,500,426 ítems; promedio 3.000852; aproximadamente 573.58 MiB.",
      archivo: "dataset/orders_500k.jsonl"
    },
    fase3: {
      nombre: "Infraestructura Docker",
      estado: "COMPLETADA",
      detalle: "MongoDB y PostgreSQL verificados con 4 CPU, 4096 MiB de memoria y 4096 MiB de swap; cgroups v2 y objetivos Prometheus activos."
    },
    fase4: {
      nombre: "Carga e indexación",
      estado: "COMPLETADA",
      detalle: "500,000 documentos por motor; promedio auditado de 3.0009 ítems; índices requeridos presentes."
    },
    fase5: {
      nombre: "Consultas y EXPLAIN",
      estado: "COMPLETADA",
      detalle: "Planes actualizados para Q1, Q2 Top-1000 y Q2_SORT_ALL, con variantes de memoria."
    },
    fase6: {
      nombre: "Runner y telemetría",
      estado: "COMPLETADA",
      detalle: "Piloto Q1 de 30 segundos y concurrencia 1 en ambos motores; archivos CSV con 14 columnas validados."
    },
    fase7: {
      nombre: "Matriz de benchmarks",
      estado: "EJECUCION_PARCIAL; 99/108 claves SUCCESS",
      pasos: {
        "7.1": "COMPLETADO: matriz oficial de 108 corridas: 36 celdas × 3 repeticiones.",
        "7.2": "COMPLETADO: mediciones.csv conserva filas de las 108 claves y los estados de intentos.",
        "7.3": "COMPLETADO: run_benchmarks.ps1 ejecuta, reanuda y registra fallos; stderr del runner queda preservado.",
        "7.4": "PARCIAL: 99 claves SUCCESS; 9 claves de PostgreSQL Q1/concurrencia 50 quedaron sin éxito por falta de /dev/shm."
      }
    },
    fase8: {
      nombre: "Análisis, gráficas e informe",
      estado: "ANALISIS_PARCIAL_COMPLETADO",
      pasos: {
        "8.1": "COMPLETADO: analisis/graficador.py valida el CSV, deduplica por clave SUCCESS, detecta las 9 claves incompletas y produce resumenes.",
        "8.2": "COMPLETADO: graficas P99/concurrencia, throttling/throughput y curva RSS historica de Prometheus (15 s).",
        "8.3": "COMPLETADO: reporte compara EXPLAIN preparatorios y separa esas evidencias de las corridas.",
        "8.4": "COMPLETADO COMO REPORTE PARCIAL: siete secciones con cobertura, limitaciones, fallos y recomendaciones."
      },
      artefactos: [
        "reporte_final_metricas.md",
        "analisis/resumen_por_celda.csv",
        "analisis/resumen_por_motor_query.csv",
        "analisis/graficas/latencia_p99_concurrencia.png",
        "analisis/graficas/throttling_vs_throughput.png",
        "analisis/graficas/rss_tiempo.png"
      ],
      limitacion: "La matriz permanece incompleta: PostgreSQL Q1/concurrencia 50 tiene 9 claves sin SUCCESS. El informe no es un resultado final balanceado."
    }
  },

  solicitudesYAcciones: [
    {
      usuario: "Pidió investigar el experimento y verificar si estaba cerca de terminar.",
      asistente: "Revisó documentación, scripts, Compose, dataset, pilotos y contenedores; identificó como pendientes la matriz y el reporte final."
    },
    {
      usuario: "Pidió modificar lo necesario, sin hacer todavía las pruebas, y saber si todo estaba listo para generarlas.",
      asistente: "Corrigió runner, recolector, Compose, dependencias, generador y documentación; agregó el orquestador protegido por -ConfirmRun y no inició la matriz."
    },
    {
      usuario: "Pidió marcar el estado de cada fase hasta la 6.",
      asistente: "Actualizó el checklist por fases y registró evidencias."
    },
    {
      usuario: "Pidió ir fase por fase, preguntando si están completas y solicitando permiso si no lo están.",
      asistente: "Adoptó el avance controlado con confirmación/autorización antes de completar trabajo pendiente."
    },
    {
      usuario: "Autorizó completar las fases pendientes hasta la 6.",
      asistente: "Regeneró y validó dataset; recreó/verificó infraestructura; recargó y auditó orders; generó EXPLAIN; corrió piloto Q1 de 30 segundos en MongoDB y PostgreSQL. Fases 1–6 quedaron completas."
    },
    {
      usuario: "Preguntó si ya se podían ejecutar las pruebas.",
      asistente: "Ejecutó preflight sin -ConfirmRun: en esa etapa planificó 216 corridas, estimó al menos 25 h 12 min y no inició la matriz. Ese diseño fue sustituido después por la matriz oficial del PDF de 108 corridas."
    },
    {
      usuario: "Autorizó corregir Q2 y verificarla con EXPLAIN, sin lanzar la matriz.",
      asistente: "Ajustó Q2_SORT_ALL y verificó los planes de ambas bases de datos y variantes de memoria."
    },
    {
      usuario: "Autorizó un piloto específico de Q2_SORT_ALL.",
      asistente: "Ejecutó cuatro variantes y validó sus estados y el CSV."
    },
    {
      usuario: "Preguntó si se pueden hacer las pruebas y si ya se hizo un piloto.",
      asistente: "Aclaró que sí se hicieron pilotos de validación, pero no la matriz completa."
    },
    {
      usuario: "Pidió guardar toda la memoria y lo realizado en un archivo .js dentro de Agente.",
      asistente: "Actualizó index.js con estado, acciones, decisiones, resultados y cronología."
    },
    {
      usuario: "Eligió «wait» cuando se le preguntó si iniciar la matriz ampliada de 216 corridas.",
      asistente: "Dejó la matriz sin iniciar y Fase 7 pendiente."
    },
    {
      usuario: "Aclaró que quería guardar cada solicitud y memoria del asistente, no solo el resumen técnico.",
      asistente: "Añadió una cronología de solicitudes y acciones a index.js."
    },
    {
      usuario: "Aclaró que el archivo debía llevar el nombre del asistente y ser nuevo, no el archivo existente.",
      asistente: "Creó este archivo independiente Agente/AsistenteCopilot.js; index.js debe conservarse sin modificar por esta solicitud."
    },
    {
      usuario: "Pidió ajustar el experimento a lo indicado en el PDF y confirmar que esté listo antes de ejecutar la matriz.",
      asistente: "Se identificó que el PDF calcula 108 corridas con Q1 y Q2, mientras el usuario aclaró que quiere 216. Se pidió precisar el diseño antes de cambiar o ejecutar la matriz."
    },
    {
      usuario: "Aclaró que el total deseado es 216, entendiendo 108 por cada perfil, y eligió el diseño actual de 216.",
      asistente: "Se documentó correctamente que el diseño actual equivale a 108 por motor, no por perfil de recursos; incluye Q1, Q2 Top-1000 y Q2_SORT_ALL con dos variantes. Se explicó que Q2_SORT_ALL amplía la fórmula del PDF."
    },
    {
      usuario: "Confirmó el diseño actual de 216 corridas y pidió dejarlo listo, pero avisar antes de ejecutar la matriz.",
      asistente: "Se actualizaron orquestador y documentos para describir 216 corridas (108 por motor), distinguiendo la extensión Q2_SORT_ALL de las 108 corridas de Q1/Q2 indicadas por la fórmula del PDF. El preflight planificó 216 corridas sin ejecutar ninguna ni crear mediciones.csv; sintaxis PowerShell/Python/JavaScript validada."
    },
    {
      usuario: "Estableció playbook.pdf como referencia oficial y aprobó la matriz de la sección 6: 108 corridas, Q1/Q2, y pidió actualizar documentos, orquestador y controles sin ejecutar pruebas.",
      asistente: "Se alinearon los archivos al diseño de 108 corridas (36 celdas × 3 repeticiones); se fijaron Q2 en allowDiskUse=false para MongoDB y work_mem=4MB para PostgreSQL. Q2_SORT_ALL y variantes altas quedan fuera, salvo aprobación posterior."
    },
    {
      usuario: "Solicitó únicamente validaciones, preflight y verificaciones de configuración, sin iniciar las pruebas.",
      asistente: "El preflight confirmó 108 corridas, 36 celdas y 3 repeticiones por celda. Sintaxis PowerShell/Python/JavaScript y configuración Compose validadas; no se creó mediciones.csv ni se inició la matriz."
    },
    {
      usuario: "Pidió el estado final de preparación y una validación mínima no oficial para comprobar el pipeline.",
      asistente: "Se verificaron los dos motores con 500,000 registros cada uno, Compose y tres objetivos Prometheus saludables. Piloto no oficial Q2 Top-1000 (2 s warmup + 10 s medición, concurrencia 1): MongoDB 12 consultas, 1.11 QPS, SUCCESS; PostgreSQL 39 consultas, 3.81 QPS, SUCCESS. CSV piloto independiente validado con 14 columnas y dos filas."
    },
    {
      usuario: "Estableció el PDF como referencia oficial y aprobó solo su matriz: 108 corridas, 36 celdas, Q1/Q2 y 3 repeticiones; pidió no ejecutar todavía.",
      asistente: "Se retiró Q2_SORT_ALL y las variantes extendidas del orquestador y de la documentación oficial. Q2 queda fija en allowDiskUse=false (MongoDB) y work_mem=4MB (PostgreSQL). El preflight confirmó 108 corridas sin ejecutar la matriz ni crear mediciones.csv."
    },
    {
      usuario: "Aceptó el estado de preparación, la evidencia y los riesgos residuales; pidió conservar la matriz oficial de 108 corridas y la reanudación, e indicó que autorizará la ejecución en la siguiente instrucción.",
      asistente: "Se conserva la configuración y reanudación del protocolo oficial. No iniciar ninguna corrida oficial hasta recibir la autorización explícita posterior."
    },
    {
      usuario: "Autorizó explícitamente iniciar la matriz oficial de 108 corridas de la sección 6, con dos motores, tres perfiles, Q1/Q2, concurrencias 1/10/50, tres repeticiones y reanudación mediante el CSV oficial; pidió registrar fallos y entregar el resumen al finalizar.",
      asistente: "La matriz oficial se inició con auditoría inicial de datos e índices. Se completaron 66 claves exitosas antes de una interrupción; se conservó el CSV oficial para reanudar."
    },
    {
      usuario: "Notificó la salida con error del proceso de ejecución en segundo plano.",
      asistente: "Se inspeccionaron CSV, logs, marcador y procesos. La ejecución se había detenido en PostgreSQL PROFILE_A_BASELINE/Q1/concurrencia 50/repetición 1. El log de PostgreSQL confirmó falta de espacio en /dev/shm durante el warmup. Se corrigió la captura de stderr y el orquestador para registrar un escenario fallido y continuar."
    },
    {
      usuario: "Recibió notificación de fin del proceso que reanudó el resto de escenarios.",
      asistente: "La ejecución terminó de procesar las claves restantes: 99 claves únicas SUCCESS, 9 claves sin éxito (8 ABORTED y 1 PARTIAL_FAILURE). Los nueve casos no exitosos corresponden a PostgreSQL Q1 con concurrencia 50 en perfiles A/B/C; la causa recurrente fue agotamiento de /dev/shm. No se cambiaron límites experimentales. Fase 7 permanece incompleta y se requiere decidir si se preservan los fallos o se autoriza aumentar la memoria compartida y reintentar."
    },
    {
      usuario: "Eligió conservar la configuración actual y reportar 99 corridas exitosas y 9 fallidas, sin aumentar shm_size.",
      asistente: "Se conserva el CSV original y sus fallos tal como quedaron. No se reintentan las nueve claves ni se modifica la configuración Docker; Fase 7 queda incompleta y Fase 8 no debe analizar la matriz como si estuviera completa."
    },
    {
      usuario: "Indicó continuar con el plan de trabajo tras conservar el resultado parcial.",
      asistente: "Se completó la fase 8 como análisis parcial: se creó analisis/graficador.py, se generaron resúmenes por celda y motor/query, tres gráficas (P99, throttling/QPS y RSS histórico Prometheus a 15 s) y reporte_final_metricas.md con las siete secciones. El reporte distingue 99 claves SUCCESS de las nueve incompletas, compara 15 de 18 bloques emparejados completos y limita conclusiones."
    }
  ],

  resultadosPilotos: {
    q1: {
      duracionSegundos: 30,
      concurrencia: 1,
      MongoDB: { consultas: 13, qps: 0.42, estado: "SUCCESS" },
      PostgreSQL: { consultas: 3, qps: 0.09, estado: "SUCCESS" },
      archivo: "mediciones_piloto_fase6.csv"
    },
    q2SortAll: {
      MongoDB_sin_allowDiskUse: {
        estado: "FAIL_MEMORY_LIMIT",
        detalle: "Código 292; límite de 100 MB excedido; spill=false."
      },
      MongoDB_con_allowDiskUse: {
        consultas: 14,
        qps: 0.46,
        estado: "SUCCESS",
        spill: true,
        spills: 3
      },
      PostgreSQL_work_mem_4MB: {
        consultas: 44,
        qps: 1.47,
        estado: "SUCCESS",
        spill: true,
        plan: "external merge; 2680 KB temporales."
      },
      PostgreSQL_work_mem_64MB: {
        consultas: 44,
        qps: 1.44,
        estado: "SUCCESS",
        spill: false,
        plan: "quicksort; 10702 KB de memoria."
      },
      archivo: "mediciones_piloto_q2.csv"
    }
  },

  archivosImportantes: {
    planFases: "Contexto/06_plan_de_trabajo_fases.md",
    analisis: "analisis/graficador.py",
    reporteMetricas: "reporte_final_metricas.md",
    auditoria: "Contexto/07_auditoria_del_sistema.md",
    orquestador: "run_benchmarks.ps1",
    runner: "benchmark_runner/runner.py",
    recolector: "benchmark_runner/metrics_collector.py",
    explain: "Contexto/09_planes_de_ejecucion_explain.md",
    pilotoQ1: "mediciones_piloto_fase6.csv",
    pilotoQ2: "mediciones_piloto_q2.csv",
    memoriaAnterior: "Agente/index.js"
  },

  cambiosPrincipales: [
    "Se creó run_benchmarks.ps1; por defecto hace preflight y requiere -ConfirmRun para iniciar la matriz.",
    "Se añadieron consultas Q2_SORT_ALL para MongoDB y PostgreSQL.",
    "Se mejoraron runner y recolector para estados de error, telemetría y detección de spill.",
    "Se ajustaron límites de swap, generación del dataset, auditoría de bases y generación de EXPLAIN.",
    "Se actualizaron documentos de contexto y fases."
  ],

  siguientePaso: "Entregar el reporte como parcial; mantener Fase 7 incompleta y no iniciar una nueva medición ni cambiar shm_size, pues el usuario decidió conservar los nueve fallos y la configuración actual."
};
