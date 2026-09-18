# V2 — Contratos de datos

Este documento define los contratos mínimos de los productos V2 antes de escribir la lógica que los genera. Los contratos complementan, pero no modifican, el contrato analítico congelado de V1.

## Reglas comunes

- La clave heredada es `(km_inicio, km_fin)`, con cobertura exacta desde `0–1` hasta `129–130`.
- `segment_id` es una clave V2 derivada de forma determinista: `seg_000_001`, …, `seg_129_130`.
- Los archivos serán CSV UTF-8, con encabezados en `lowercase_snake_case`.
- El orden canónico es ascendente por `km_inicio`; los desempates se definen en cada producto.
- `fuente` y `source_version` son obligatorios cuando el producto incorpora evidencia externa o una transformación versionada.
- Los instantes usan UTC y formato ISO 8601.
- Los valores ausentes permanecen explícitos; el conjunto canónico no aplica imputación silenciosa.
- Ningún valor infinito o `NaN` textual se admite en productos publicados.
- Toda simulación debe identificarse a nivel de fila, no solo en el nombre del archivo.
- Cada generador debe ser determinista con entradas, configuración y semilla equivalentes.

## A. `segment_neighbors.csv`

Lista dirigida de aristas para el grafo lineal de primer orden.

### Columnas

| Columna | Tipo | Regla |
|---|---|---|
| `segment_id` | string | Segmento origen; patrón `seg_NNN_NNN` |
| `km_inicio` | integer | Límite inicial del origen |
| `km_fin` | integer | Límite final del origen; `km_fin - km_inicio = 1` |
| `neighbor_segment_id` | string | Segmento vecino |
| `neighbor_km_inicio` | integer | Límite inicial del vecino |
| `neighbor_km_fin` | integer | Límite final del vecino |
| `distance_order` | integer | `1` en la primera versión |
| `weight` | float | `1.0` antes de cualquier normalización analítica |
| `fuente` | string | `derived:v1_segment_order` |

### Invariantes

- 130 nodos distintos.
- 258 aristas dirigidas: cada una de las 129 relaciones físicas aparece en ambos sentidos.
- Los extremos km 0–1 y km 129–130 tienen grado 1; los demás, grado 2.
- El grafo es conexo, sin autoaristas ni duplicados.
- Toda arista es recíproca.
- Solo se conectan segmentos con límites kilométricos contiguos.
- Orden: `km_inicio`, luego `neighbor_km_inicio`.

## B. `segment_evidence_snapshots.csv`

Tabla longitudinal en formato largo. Una fila representa el valor de una métrica para un segmento en un instante.

### Columnas

| Columna | Tipo | Regla |
|---|---|---|
| `segment_id` | string | Referencia válida a un segmento V1 |
| `km_inicio` | integer | Debe coincidir con `segment_id` |
| `km_fin` | integer | Debe coincidir con `segment_id` |
| `observed_at_utc` | datetime | Momento al que corresponde la evidencia |
| `ingested_at_utc` | datetime | Momento de incorporación; no anterior sin justificación documentada |
| `metric_name` | string | Nombre estable de la métrica |
| `metric_value` | float | Valor en la unidad declarada; puede estar vacío si la calidad lo exige |
| `unit` | string | Unidad explícita y estable por métrica |
| `evidence_type` | enum | `observed`, `derived` o `simulated` |
| `fuente` | string | Sistema, dataset o procedimiento de origen |
| `source_version` | string | Versión, fecha de corte o hash |
| `uncertainty_lower` | float/null | Límite inferior, si existe |
| `uncertainty_upper` | float/null | Límite superior, si existe |
| `quality_flag` | string | Estado de calidad controlado |
| `is_simulated` | boolean | Identificación obligatoria |
| `simulation_scenario_id` | string/null | Obligatorio cuando `is_simulated=true` |
| `notes` | string/null | Observación breve, no sustitutiva de metadatos |

### Invariantes

- `evidence_type=simulated` si y solo si `is_simulated=true`.
- Una fila simulada requiere `simulation_scenario_id` y una `fuente` identificable como simulación.
- Una fila no simulada debe dejar `simulation_scenario_id` vacío.
- Cuando ambos límites de incertidumbre existen: `lower <= metric_value <= upper`.
- La clave lógica es `(segment_id, observed_at_utc, metric_name, fuente, source_version, simulation_scenario_id)`.
- Correcciones de evidencia se versionan; no se sobrescriben sin trazabilidad.

## C. `segment_change_events.csv`

Diferencias deterministas entre dos snapshots comparables.

### Columnas

| Columna | Tipo | Regla |
|---|---|---|
| `change_event_id` | string | Identificador determinista del par comparado |
| `segment_id` | string | Segmento afectado |
| `baseline_snapshot_at_utc` | datetime | Instante base |
| `current_snapshot_at_utc` | datetime | Instante actual; posterior al base |
| `metric_name` | string | Misma métrica y unidad en ambos snapshots |
| `baseline_value` | float | Valor base |
| `current_value` | float | Valor actual |
| `delta_abs` | float | `current_value - baseline_value` |
| `delta_pct` | float/null | Cambio relativo; vacío cuando la base es cero |
| `change_direction` | enum | `increase`, `decrease` o `stable` |
| `change_class` | string | Clase determinada por configuración versionada |
| `confidence` | float | Escala `0–1`; refleja evidencia, no causalidad |
| `is_simulated` | boolean | Heredado de las evidencias utilizadas |
| `simulation_scenario_id` | string/null | Obligatorio si el evento es simulado |
| `fuente` | string | Procedimiento generador |
| `source_version` | string | Versión de reglas y umbrales |

### Invariantes

- `baseline_snapshot_at_utc < current_snapshot_at_utc`.
- Valores, unidad y definición de la métrica son comparables.
- `delta_abs` y `delta_pct` se recalculan en pruebas, no se aceptan como datos opacos.
- Un evento no declara causa, probabilidad de falla ni necesidad automática de intervención.
- Si cualquiera de las entradas es simulada, el evento completo es simulado.

## D. `segment_priority.csv`

Salida por escenario para priorización relativa y análisis de estabilidad.

### Columnas

| Columna | Tipo | Regla |
|---|---|---|
| `segment_id` | string | Segmento V2 |
| `km_inicio` | integer | Límite inicial |
| `km_fin` | integer | Límite final |
| `scenario_id` | string | Configuración reproducible |
| `priority_score` | float | Escala documentada; no equivale a riesgo absoluto |
| `rank_median` | float | Mediana del rango |
| `rank_p10` | float | Percentil 10 del rango |
| `rank_p90` | float | Percentil 90 del rango |
| `p_top10` | float | Probabilidad empírica de aparecer entre los 10 primeros |
| `p_top20` | float | Probabilidad empírica de aparecer entre los 20 primeros |
| `confidence_class` | string | Clase basada en cobertura, calidad y estabilidad |
| `dominant_driver` | string | Principal contribución explicable |
| `is_simulated` | boolean | Verdadero si interviene evidencia simulada |
| `fuente` | string | Procedimiento de priorización |
| `source_version` | string | Versión de código/configuración |

### Invariantes

- `0 <= p_top10 <= p_top20 <= 1`.
- `1 <= rank_p10, rank_median, rank_p90 <= 130`.
- Los nombres de percentiles describen la distribución numérica del rango; la interpretación de “mejor” o “peor” debe explicitarse.
- Un escenario mixto con cualquier entrada simulada se marca como simulado.
- La prioridad es relativa al corredor y al escenario. No se denomina predicción, riesgo absoluto ni recomendación de seguridad.

## Controles de calidad transversales

1. **Cobertura:** claves V2 válidas contra los 130 segmentos V1.
2. **Integridad referencial:** ningún vecino, snapshot, evento o resultado apunta a un segmento inexistente.
3. **Segregación de simulación:** consistencia entre `evidence_type`, `is_simulated` y `simulation_scenario_id`.
4. **Temporalidad:** orden de timestamps y ausencia de comparaciones incompatibles.
5. **Incertidumbre:** límites ordenados, probabilidades acotadas e intervalos interpretables.
6. **Numerical QA:** sin infinitos, `NaN` textuales ni divisiones por cero ocultas.
7. **Reproducibilidad:** orden estable, configuración versionada y semilla registrada cuando corresponda.
8. **Regresión V1:** `tests/test_analytical_v1_contract.py` debe continuar pasando sin cambios.

## Pruebas previstas para la Fase 1 y posteriores

- `test_v2_segment_identity_contract.py`
- `test_v2_neighbor_graph_contract.py`
- `test_v2_evidence_snapshot_contract.py`
- `test_v2_change_event_contract.py`
- `test_v2_priority_contract.py`
- `test_v1_outputs_unchanged.py`

## Lenguaje permitido

- “exposición relativa V1”
- “cambio observado/derivado/simulado”
- “prioridad relativa bajo el escenario X”
- “segmento con evidencia incompleta”
- “resultado sensible a pesos o supuestos”

## Lenguaje no permitido sin evidencia adicional

- “predice una falla”
- “segmento seguro/inseguro”
- “riesgo absoluto”
- “causa del deterioro”
- “intervención obligatoria”
- “precisión del modelo” sin objetivo real, partición espacial y conjunto de prueba independiente
