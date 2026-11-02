/**
 * Memoria persistente del experimento MongoDB vs. PostgreSQL JSONB.
 * Actualizar este registro al cambiar fases, resultados o decisiones del usuario.
 */

module.exports = {
  agente: {
    nombre: "Asistente de experimento",
    rol: "Apoyar la preparación, ejecución controlada y documentación del benchmark",
    ultimaActualizacion: new Date().toISOString()
  },

  experimento: {
    objetivo: "Comparar el rendimiento de MongoDB y PostgreSQL JSONB con un dataset y cargas de trabajo equivalentes.",
    entorno: {
      sistema: "Windows con Docker Desktop/WSL2 y cgroups v2",
      cpuHost: 8,
      memoriaHostAproximadaGiB: 5.635,
      recursosContenedoresVerificados: {
        cpu: 4,
        memoriaMiB: 4096,
        memorySwapMiB: 4096
      },
      puertos: {
        postgresHost: 5433,
        cadvisorHost: 8085,
        prometheusHost: 9090
      }
    },
    dataset: {
      ruta: "dataset/orders_500k.jsonl",
      registros: 500000,
      itemsTotales: 1500426,
      promedioItemsPorRegistro: 3.000852,
      tamanoAproximadoMiB: 573.58,
      valido: true
    },
    matriz: {
      corridasPlaneadas: 108,
      celdas: 36,
      repeticionesPorCelda: 3,
      corridasPorMotor: 54,
      corridasPorPerfil: 36,
      consultas: ["Q1", "Q2 Top-1000"],
      configuracionQ2: {
        mongodb: "allowDiskUse=false",
        postgresql: "work_mem=4MB"
      },
      escenariosExcluidos: ["Q2_SORT_ALL", "allowDiskUse=true", "work_mem=64MB"],
      estimacionMinima: "12 h 36 min",
      iniciada: false,
      csvOficialGenerado: false,
      csvOficial: "mediciones.csv"
    }
  },

  reglasDeContinuidad: [
    "Avanzar fase por fase y consultar al usuario si considera completa la fase.",
    "Si una fase no está completa, preguntar si autoriza completarla antes de ejecutar acciones.",
    "No iniciar la matriz oficial de 108 corridas sin autorización explícita.",
    "El preflight de run_benchmarks.ps1 no ejecuta la matriz; -ConfirmRun sí la inicia.",
    "No afirmar que la matriz fue ejecutada: hasta el último estado registrado, sigue pendiente.",
    "Las pruebas piloto y EXPLAIN sí fueron autorizados y ejecutados por separado."
  ],

  estadoFases: {
    fase1: { nombre: "Preparación del entorno y dependencias", estado: "COMPLETADA" },
    fase2: {
      nombre: "Generador del dataset sintético",
      estado: "COMPLETADA",
      evidencia: "500,000 registros JSON válidos; 1,500,426 ítems; promedio 3.000852."
    },
    fase3: {
      nombre: "Infraestructura Docker y perfiles de recursos",
      estado: "COMPLETADA",
      evidencia: "MongoDB y PostgreSQL verificados con 4 CPU, 4096 MiB RAM y 4096 MiB de swap; Prometheus activo."
    },
    fase4: {
      nombre: "Ingesta e indexación",
      estado: "COMPLETADA",
      evidencia: "500,000 documentos en cada motor; promedio auditado 3.0009 ítems e índices requeridos presentes."
    },
    fase5: {
      nombre: "Consultas y planes de ejecución",
      estado: "COMPLETADA",
      evidencia: "EXPLAIN actualizado para Q1, Q2 Top-1000 y Q2_SORT_ALL, incluyendo variantes de memoria."
    },
    fase6: {
      nombre: "Runner y telemetría",
      estado: "COMPLETADA",
      evidencia: "Piloto Q1 de 30 s y concurrencia 1 ejecutado en ambos motores; dos filas CSV de 14 columnas con estado SUCCESS."
    },
    fase7: {
      nombre: "Automatización y ejecución de la matriz",
      estado: "PREPARADA_PENDIENTE_DE_AUTORIZACION",
      pasos: {
        "7.1": "COMPLETADO: matriz oficial definida: 108 corridas, 36 celdas y 3 repeticiones por celda.",
        "7.2": "PENDIENTE: mediciones.csv se crea al iniciar la ejecución completa.",
        "7.3": "COMPLETADO: run_benchmarks.ps1 creado; requiere -ConfirmRun para ejecutar.",
        "7.4": "PENDIENTE: matriz completa no iniciada."
      }
    },
    fase8: {
      nombre: "Análisis estadístico, gráficas e informe",
      estado: "PENDIENTE",
      pasos: {
        "8.1": "PENDIENTE: crear analisis/graficador.py.",
        "8.2": "PENDIENTE: generar gráficas obligatorias.",
        "8.3": "PENDIENTE: análisis comparativo de planes.",
        "8.4": "PENDIENTE: reporte_final_metricas.md."
      }
    }
  },

  cambiosRealizados: {
    archivosNuevos: [
      "run_benchmarks.ps1",
      "queries/mongo_q2_sort_all.js",
      "queries/postgres_q2_sort_all.sql"
    ],
    archivosActualizados: [
      "benchmark_runner/runner.py",
      "benchmark_runner/metrics_collector.py",
      "docker-compose.yml",
      "requirements.txt",
      "synthetic_data_generator.py",
      "scripts/audit_databases.py",
      "scripts/generate_explain_plans.py",
      "Contexto/02_dataset_y_atributos.md",
      "Contexto/03_perfiles_docker_recursos.md",
      "Contexto/04_cargas_de_trabajo_queries.md",
      "Contexto/05_protocolo_telemetria_kpis.md",
      "Contexto/06_plan_de_trabajo_fases.md",
      "Contexto/07_auditoria_del_sistema.md",
      "Contexto/08_revision_de_requisitos_y_puntos_criticos.md",
      "Contexto/09_planes_de_ejecucion_explain.md"
    ],
    resumenTecnico: [
      "El runner soporta Q1, Q2 Top-1000 y Q2_SORT_ALL, variantes de memoria, telemetría y estados explícitos de error.",
      "El recolector reporta errores de Prometheus, RSS máximo y métricas sumadas.",
      "Docker Compose fija el límite de swap igual a la memoria configurada.",
      "El generador produce en promedio tres ítems por orden y la auditoría valida conteos, promedio e índices.",
      "Q2 Top-1000 se mantiene separada de Q2_SORT_ALL y no presupone spill."
    ]
  },

  pilotos: [
    {
      nombre: "Q1 - validación del runner",
      duracionSegundos: 30,
      concurrencia: 1,
      resultados: {
        MongoDB: { consultas: 13, qps: 0.42, estado: "SUCCESS" },
        PostgreSQL: { consultas: 3, qps: 0.09, estado: "SUCCESS" }
      },
      evidencia: "mediciones_piloto_fase6.csv; encabezado reglamentario y 14 columnas en ambas filas."
    },
    {
      nombre: "Q2_SORT_ALL - validación de memoria y spill",
      resultados: {
        "MongoDB sin allowDiskUse": {
          estado: "FAIL_MEMORY_LIMIT",
          detalle: "Código 292; excedió el límite de 100 MB; spill=false."
        },
        "MongoDB con allowDiskUse=true": {
          consultas: 14,
          qps: 0.46,
          estado: "SUCCESS",
          spill: true,
          spills: 3
        },
        "PostgreSQL work_mem=4MB": {
          consultas: 44,
          qps: 1.47,
          estado: "SUCCESS",
          spill: true,
          plan: "external merge; 2680 KB de archivos temporales."
        },
        "PostgreSQL work_mem=64MB": {
          consultas: 44,
          qps: 1.44,
          estado: "SUCCESS",
          spill: false,
          plan: "quicksort; 10702 KB de memoria."
        }
      },
      evidencia: "mediciones_piloto_q2.csv; cuatro filas con 14 columnas."
    }
  ],

  historialYDecisiones: [
    "Se preparó y revisó el experimento MongoDB vs. PostgreSQL JSONB.",
    "Se corrigieron problemas de medición de spill, swap, distribución de ítems y telemetría.",
    "El usuario autorizó regenerar el dataset, recrear los motores y reemplazar únicamente la colección/tabla orders.",
    "El usuario autorizó actualizar y ejecutar EXPLAIN; no autorizó la matriz completa.",
    "El usuario autorizó los pilotos Q1 y Q2_SORT_ALL.",
    "El preflight sin -ConfirmRun planificó 216 corridas y estimó un mínimo de 25 h 12 min; no ejecutó la matriz ni creó mediciones.csv.",
    "Se preguntó si iniciar la matriz ampliada o esperar; el usuario eligió esperar.",
    "El usuario confirmó como diseño oficial la matriz de la sección 6 del playbook: 108 corridas con Q1/Q2; escenarios extra excluidos salvo aprobación explícita.",
    "Se validó estáticamente el orquestador, el compose y los archivos Python/JavaScript. El preflight confirmó 108 corridas, 36 celdas y 3 repeticiones, sin ejecutar mediciones ni crear mediciones.csv."
  ],

  historialConversacion: [
    {
      orden: 1,
      solicitud: "«necesito que te informes todo sobre el experimento que estamos haciendo creo que ya estamos casi por terminar puedes verificarlo?»",
      respuestaYAccion: "Se revisó el experimento, documentación, scripts, Compose, dataset, pilotos y estado de los contenedores. Se identificó que la matriz completa y el reporte final seguían pendientes."
    },
    {
      orden: 2,
      solicitud: "«lo puedes modificar pero todavia no hagas las pruebas (necesito que me digas si tenemos todo para generar las pruebras)»",
      respuestaYAccion: "Se corrigieron y prepararon runner, recolector, Compose, dependencias, generador y documentación. Se agregó run_benchmarks.ps1 con protección -ConfirmRun. No se inició la matriz."
    },
    {
      orden: 3,
      solicitud: "«ahora necesito que vayas marcando si esta completo los pasos de cada fase hasta la 6 porfavor»",
      respuestaYAccion: "Se revisó el checklist de fases y se actualizó progresivamente con las evidencias disponibles."
    },
    {
      orden: 4,
      solicitud: "«vamis fase por fase y me vas preguntando si estan completados y si no me preguntas si queremos completarlos porfavor»",
      respuestaYAccion: "Se adoptó el flujo de confirmar cada fase con el usuario y pedir autorización antes de completar trabajo pendiente."
    },
    {
      orden: 5,
      solicitud: "Confirmar y completar las fases pendientes hasta la Fase 6; el usuario autorizó las acciones controladas necesarias.",
      respuestaYAccion: "Fase 1 confirmada. Con autorización, se regeneró y validó el dataset de 500,000 registros (Fase 2), se verificó infraestructura (Fase 3), se recargaron y auditaron ambos motores (Fase 4), se generaron EXPLAIN (Fase 5) y se ejecutó el piloto Q1 de 30 segundos en MongoDB y PostgreSQL (Fase 6). Las fases 1–6 quedaron marcadas completas."
    },
    {
      orden: 6,
      solicitud: "Verificar si ya se podían ejecutar las pruebas.",
      respuestaYAccion: "Se ejecutó solamente el preflight seguro del orquestador, sin -ConfirmRun. Planificó 216 corridas y estimó al menos 25 h 12 min; no ejecutó la matriz ni creó mediciones.csv."
    },
    {
      orden: 7,
      solicitud: "Corregir Q2 y verificarla con EXPLAIN, sin lanzar la matriz.",
      respuestaYAccion: "Se ajustó Q2_SORT_ALL y se validaron sus planes. PostgreSQL mostró external merge con work_mem=4MB y quicksort con 64MB; MongoDB superó 100MB sin allowDiskUse y reportó spill con allowDiskUse."
    },
    {
      orden: 8,
      solicitud: "Autorizar un piloto específico de Q2_SORT_ALL.",
      respuestaYAccion: "Se ejecutaron cuatro variantes piloto. MongoDB sin disco terminó FAIL_MEMORY_LIMIT; MongoDB con allowDiskUse y PostgreSQL con 4MB/64MB terminaron SUCCESS. Se validó el CSV de cuatro filas y 14 columnas."
    },
    {
      orden: 9,
      solicitud: "«pero entonces si se pueden hacer las pruebas e hiciste una prueba piloto para ver que funcionara cierto?»",
      respuestaYAccion: "Se aclaró que los pilotos validaron el proceso, pero la matriz completa aún no se había ejecutado y requería autorización."
    },
    {
      orden: 10,
      solicitud: "«antes de eso quiero que en la carpeta agente en un archivo .js guardes toda la memoria y lo que has hecho hasta ahora porfavor»",
      respuestaYAccion: "Se actualizó Agente/index.js con el estado del proyecto, resultados de pilotos, archivos modificados, decisiones y pendientes. Se validó con node --check."
    },
    {
      orden: 11,
      solicitud: "Ante la pregunta de si iniciar la matriz completa, el usuario respondió: «wait».",
      respuestaYAccion: "Se dejó la matriz sin iniciar y se confirmó que Fase 7 está preparada pero pendiente de autorización."
    },
    {
      orden: 12,
      solicitud: "«tambien lo que me refiero es a ti cada solicitud que has hecho que guardes toda tu memoria en un archivo .js»",
      respuestaYAccion: "Se interpretó como una aclaración para guardar también las solicitudes del usuario y las acciones/respuestas asociadas en una cronología dentro de Agente/index.js."
    },
    {
      orden: 13,
      solicitud: "Tomar playbook.pdf como referencia oficial y actualizar documentación, orquestador y archivos de control a la matriz aprobada de la sección 6: 108 corridas, solo validaciones y preflight, sin ejecutar las pruebas.",
      respuestaYAccion: "Se actualizó el control del proyecto para 36 celdas × 3 repeticiones; Q1/Q2 únicamente. Se excluyeron Q2_SORT_ALL y variantes adicionales. Q2 queda fijada en allowDiskUse=false para MongoDB y work_mem=4MB para PostgreSQL. Se hará solo validación y preflight."
    },
    {
      orden: 14,
      solicitud: "Validar y hacer preflight, sin ejecutar las pruebas.",
      respuestaYAccion: "El preflight confirmó 108 corridas, 36 celdas y 3 repeticiones por celda. La sintaxis PowerShell/Python/JavaScript y docker compose config pasaron; mediciones.csv no se creó y no se ejecutó la matriz."
    }
  ],

  archivosDeResultados: {
    pilotoQ1: "mediciones_piloto_fase6.csv",
    pilotoQ2: "mediciones_piloto_q2.csv",
    matrizCompleta: "mediciones.csv (todavía no generado)"
  },

  siguienteAccion: "Informar que el diseño oficial de 108 corridas está preparado y esperar autorización explícita. No ejecutar con -ConfirmRun hasta recibirla."
};
