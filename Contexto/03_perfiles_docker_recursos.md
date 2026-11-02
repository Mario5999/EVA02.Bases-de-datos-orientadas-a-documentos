# 03. Perfiles de Recursos (Docker cgroups v2)

Se definen 3 perfiles de contención de hardware para evaluar la degradación del rendimiento bajo estrés.

| ID Perfil | Nombre | CPUs asignadas | Límite Memoria RAM | Swap permitido | Comportamiento Esperado |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `PROFILE_A_BASELINE` | Sin contención (Baseline) | 4.0 | 4096 MB | 0 | Rendimiento óptimo, sin limitación de CPU ni presión de memoria. |
| `PROFILE_B_MEDIUM` | Contención media | 2.0 | 2048 MB | 0 | Reducción al 50% de recursos; incremento notable de latencia P95/P99. |
| `PROFILE_C_SEVERE` | Contención severa (throttling activo) | 1.0 | 1024 MB | 0 | Alta contención, CPU CFS throttling activo, alto riesgo de volcado a disco o muerte por OOM. |

---

## Mecanismos del Kernel Linux y Docker
* **CFS Throttling (Completely Fair Scheduler):** Cuando el contenedor supera la cuota de CPU asignada en una ventana de tiempo, el kernel congela la ejecución del proceso por periodos breves.
* **cgroups v2:** Permite un aislamiento estricto de memoria unificada y contabilidad de throttling en tiempo real (`cpu.stat`).
* **Swap deshabilitado para el contenedor:** Compose fija `memswap_limit` al mismo valor que el límite de memoria. En cgroups v2, esta es la configuración efectiva para impedir el uso de swap; `mem_swappiness` no se considera prueba de que el swap esté deshabilitado.
