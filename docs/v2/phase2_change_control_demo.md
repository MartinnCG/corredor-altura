# V2 — Fase 2: demostración de change control

## Advertencia

**Todos los valores de esta fase son simulados. No describen el estado del corredor, no validan la exposición V1 y no pueden utilizarse para decisiones operacionales, de seguridad o mantenimiento.**

El propósito es demostrar el mecanismo técnico antes de incorporar evidencia real.

## Pregunta demostrativa

¿Puede el sistema conservar dos observaciones por segmento, compararlas de manera reproducible y generar un evento de cambio trazable sin confundir simulación con evidencia real?

## Productos

| Archivo | Filas | Contenido |
|---|---:|---|
| `segment_evidence_snapshots.csv` | 260 | Dos snapshots simulados para cada uno de los 130 segmentos |
| `segment_change_events.csv` | 130 | Una comparación baseline–current por segmento |

Cada fila declara:

- `is_simulated=true`;
- `simulation_scenario_id=demo_change_control_v1`;
- `fuente=simulation:deterministic_change_control_demo`;
- versión del esquema;
- timestamp y procedencia;
- incertidumbre o confianza, según corresponda.

Los eventos simulados tienen `confidence=0.0` para impedir que la certeza del cálculo determinista se interprete como confianza operacional.

## Escenario artificial

La métrica `demo_surface_condition_index` usa una escala simulada de 0–100. Las zonas km 20–29, 70–74 y 100–109 fueron seleccionadas únicamente para producir patrones visibles de prueba. No se eligieron por información del corredor ni representan deterioro o mejora real.

Las fórmulas, fechas, zonas y umbrales están versionados en:

```text
config/v2_change_demo.json
```

La dirección `increase` o `decrease` describe solamente el signo matemático. No implica mejora, deterioro, causa ni intervención.

## Reproducción

```bash
python src/features/generar_change_control_demo_v2.py
python src/features/generar_change_control_demo_v2.py --check
python -m unittest discover -s tests -v
```

El modo `--check` regenera ambos productos en memoria y falla si difieren de los archivos versionados.

## Uso en QGIS

1. Cargar `segmentos.geojson`.
2. Cargar ambos CSV como tablas sin geometría.
3. Crear en QGIS un campo equivalente a `segment_id` o relacionar mediante los límites kilométricos para snapshots.
4. Unir `segment_change_events.csv` por `segment_id` para simbolizar `change_class` o `delta_abs`.
5. Mantener visible en el diseño o leyenda la indicación **SIMULATED DEMO**.

## Controles implementados

- cobertura de los 130 segmentos en ambos tiempos;
- 260 snapshots y 130 eventos únicos;
- segregación de simulación fila por fila;
- temporalidad baseline < current <= ingestion;
- recálculo de `delta_abs` y `delta_pct` desde snapshots;
- intervalos de incertidumbre coherentes;
- clases derivadas de umbrales versionados;
- regeneración determinista de ambos CSV;
- conservación de todas las pruebas e hashes de V1 y del grafo V2.

## Condición para reemplazar la simulación

Una futura fuente real deberá definir propietario, unidad, frecuencia, cobertura, procedimiento de calidad, incertidumbre, versión y autorización de uso. Se incorporará con otro `scenario_id` y nunca sobrescribirá esta demostración.
