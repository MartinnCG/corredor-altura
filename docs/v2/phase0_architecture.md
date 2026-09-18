# V2 — Fase 0: arquitectura de inteligencia por segmento

## Estado y alcance

- **Estado:** diseño aprobado para revisión; todavía no implementa cálculos ni modifica datos.
- **Rama:** `feature/v2-segment-intelligence`.
- **Base inmutable:** cierre V1 en `484f8892d3002dc0ce743f2d3d1ff5e0cc5cfba6`.
- **Cobertura:** corredor km 0–130, dividido en 130 segmentos consecutivos de un kilómetro.
- **Objetivo:** incorporar evidencia temporal, contexto espacial, control de cambios y priorización reproducible sobre los resultados congelados de V1.

V2 se construye en el mismo repositorio, pero trata V1 como una dependencia de solo lectura. El punto de partida no es volver a calcular el índice de exposición, sino transformar sus resultados en una base auditable para decisiones y experimentos posteriores.

## Límite innegociable con V1

Durante V2:

1. No se modifican archivos, fórmulas, parámetros ni resultados publicados en V1.
2. No se recalcula ni reinterpreta el índice de exposición V1.
3. No se extiende la traza más allá del km 130.
4. No se usa lenguaje predictivo sin un objetivo observado y una validación espacial adecuada.
5. No se presentan prioridades relativas como estimaciones absolutas de seguridad, falla o riesgo.
6. Los datos simulados deben permanecer identificables en cada fila y producto derivado.
7. La Fase 0 no modifica el dashboard ni añade dependencias de ejecución.

## Entradas canónicas de solo lectura

| Archivo | Función en V2 | Tratamiento |
|---|---|---|
| `data/processed/segmentos.csv` | Geometría e identidad longitudinal | Solo lectura |
| `data/processed/features_segmentos_master.csv` | Variables consolidadas por segmento | Solo lectura |
| `data/processed/indice_exposicion_segmentos.csv` | Exposición relativa V1 | Solo lectura |
| `data/processed/validacion_indice_exposicion.csv` | Evidencia de validación V1 | Solo lectura |

La identidad fuente continúa siendo `(km_inicio, km_fin)`. V2 puede derivar un `segment_id` estable para relaciones y tablas longitudinales, sin escribirlo de vuelta en los productos V1.

## Arquitectura propuesta

### 1. Identidad y trazabilidad

Construir una dimensión de segmentos estable y validar cobertura, orden, unicidad y continuidad. Toda tabla V2 debe poder volver de forma inequívoca a los límites kilométricos V1.

### 2. Grafo de adyacencia

Representar la secuencia física del corredor como un grafo lineal reproducible. La primera versión usará vecindad contigua de primer orden; pesos alternativos solo podrán añadirse como escenarios explícitos.

### 3. Evidencia temporal

Almacenar observaciones, derivados y simulaciones en formato largo, con tiempo de observación, tiempo de ingestión, fuente, versión, unidad, calidad e incertidumbre. No se sobrescriben observaciones anteriores.

### 4. Eventos de cambio

Comparar snapshots compatibles para identificar cambios por métrica y segmento. Un evento describe una diferencia reproducible; no atribuye causalidad ni implica automáticamente una intervención.

### 5. Contexto espacial y regímenes

Evaluar autocorrelación y agrupamientos sobre el grafo, y detectar tramos contiguos con perfiles semejantes. Los resultados deben declarar pesos, normalización, multiplicidad estadística y sensibilidad a parámetros.

### 6. Criticidad y priorización robusta

Combinar exposición V1, evidencia operacional disponible y contexto espacial mediante escenarios explícitos. La salida debe informar estabilidad del rango y no solo un orden puntual.

### 7. Explicabilidad y confianza

Para cada segmento priorizado, conservar los impulsores dominantes, procedencia, cobertura, banderas de calidad e intervalos de incertidumbre.

### 8. Productos de decisión

Generar tablas y capas para QGIS/dashboard únicamente después de superar los controles de calidad. La interfaz debe distinguir hechos observados, estimaciones derivadas, simulaciones y vacíos de información.

## Productos previstos

Estos archivos se crearán en fases posteriores bajo `data/processed/v2/`; no forman parte de la Fase 0:

| Producto | Propósito |
|---|---|
| `segment_neighbors.csv` | Aristas dirigidas del grafo de adyacencia |
| `segment_evidence_snapshots.csv` | Evidencia longitudinal normalizada |
| `segment_change_events.csv` | Cambios reproducibles entre snapshots |
| `segment_priority.csv` | Prioridad, estabilidad e incertidumbre por escenario |

Las salidas de análisis y diagnóstico se mantendrán separadas de los datos procesados canónicos.

## Plan incremental

| Fase | Resultado | Criterio de avance |
|---|---|---|
| 0 | Arquitectura, contratos y límites | Revisión del PR de diseño |
| 1 | Grafo lineal y pruebas contractuales | 130 nodos, 258 aristas dirigidas, conectividad y reciprocidad válidas |
| 2 | Demostración de control de cambios | Datos simulados segregados y resultados deterministas |
| 3 | Estadística espacial y regímenes | Sensibilidad documentada y validación de supuestos |
| 4 | Priorización robusta | Intervalos de rango y escenarios reproducibles |
| 5 | Integración de evidencia real | Fuente, calidad, incertidumbre y objetivo observado documentados |

## Criterios de aceptación de la Fase 0

- Los límites entre V1 y V2 son explícitos y verificables.
- Cada producto futuro tiene un contrato de datos previo a su implementación.
- Los datos simulados no pueden confundirse con evidencia real.
- La arquitectura admite QGIS y Python sin depender de un proveedor.
- No se introduce infraestructura que todavía no resuelva una necesidad demostrada.
- La siguiente fase puede implementarse como un cambio pequeño, probado y reversible.

## Registro inicial de decisiones

1. **Mismo repositorio, rama separada.** Mantiene continuidad técnica y permite comparar cada cambio con el cierre V1.
2. **V1 como dependencia inmutable.** Evita degradar la reproducibilidad ya alcanzada.
3. **Grafo explícito antes de estadística espacial.** Hace auditables las relaciones entre segmentos.
4. **Snapshots append-only.** Preserva historia y permite reconstruir cambios.
5. **Simulación marcada en cada fila.** Impide que una demostración sea presentada como evidencia observada.
6. **Sin etiqueta predictiva por ahora.** La predicción requiere una variable objetivo real, suficiente cobertura y validación espacial.
7. **Infraestructura diferida.** Agentes, orquestadores, bases espaciales y despliegue se evaluarán solo cuando exista una carga operacional que los justifique.
