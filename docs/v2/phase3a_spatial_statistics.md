# V2 — Fase 3A: estadística espacial

## Advertencia

**Este análisis utiliza exclusivamente los cambios simulados de la Fase 2. Los resultados no describen el corredor real y no permiten inferir deterioro, seguridad, causalidad ni necesidades de intervención.**

## Objetivo

Comprobar si el pipeline puede detectar y localizar dependencia espacial sobre la cadena validada de 130 segmentos, aplicando inferencia reproducible y controlando los falsos descubrimientos de los contrastes locales.

## Métodos

| Método | Función |
|---|---|
| Moran I global | Detectar autocorrelación espacial global |
| Geary C global | Contraste global más sensible a diferencias entre vecinos |
| Moran local (LISA) | Localizar cuadrantes HH, LH, LL y HL |
| Benjamini–Hochberg | Controlar FDR en los 130 contrastes locales |

La variable analizada es `delta_abs` de la métrica simulada `demo_surface_condition_index`.

## Pesos y sensibilidad

El análisis principal usa el grafo de primer orden con pesos normalizados por fila (`R`). Como control de sensibilidad, Moran I y Geary C también se calculan con pesos binarios (`B`).

Los extremos del corredor tienen un vecino y los segmentos interiores dos. Comparar `R` y `B` permite observar cuánto dependen los resultados globales de esa diferencia de grado.

## Inferencia reproducible

- 9.999 permutaciones por estadístico, para dar resolución suficiente a los pseudo-p antes de corregir 130 contrastes locales;
- semillas registradas por análisis;
- Moran local ejecutado en un solo proceso;
- pseudo-p locales ajustados mediante FDR Benjamini–Hochberg;
- `alpha = 0.05`;
- versiones de PySAL, NumPy y SciPy registradas en el resumen.

Los pseudo-p locales se calculan expresamente con alternativa bilateral. Un cuadrante LISA solo se publica como cluster cuando supera la corrección FDR; el resto se etiqueta `not_significant`.

## Dependencias aisladas

La fase usa un entorno V2 separado para no forzar actualizaciones sobre V1:

```bash
python -m venv .venv-v2
source .venv-v2/Scripts/activate  # Git Bash en Windows
python -m pip install -r requirements-v2.txt
```

Se fijan `esda==2.10.0` y `libpysal==4.15.0`. Esta combinación requiere Python 3.12 o superior y evita convertir las dependencias analíticas de V1 en una migración implícita.

## Reproducción

```bash
python src/features/calcular_estadistica_espacial_v2.py
python src/features/calcular_estadistica_espacial_v2.py --check
python -m unittest discover -s tests -v
```

## Productos

| Archivo | Contenido |
|---|---|
| `segment_local_moran.csv` | Resultado local y cluster FDR por segmento |
| `spatial_statistics_summary.json` | Moran, Geary, sensibilidad, semillas y versiones |

Ambos productos conservan `is_simulated`, `simulation_scenario_id`, fuente y aviso de no uso operacional.

## Resultado de control de la simulación

El patrón artificial produce autocorrelación global fuerte y consistente entre transformaciones: Moran I es aproximadamente `0.80` y Geary C aproximadamente `0.20`, con pseudo-p `0.0001`. Esto confirma que el pipeline reconoce las bandas contiguas introducidas deliberadamente.

Sin embargo, 13 segmentos superan inicialmente `p_sim <= 0.05` y **ninguno permanece significativo después de FDR bilateral**. El producto, por lo tanto, etiqueta los 130 segmentos como `not_significant`. No se relajó el criterio para obtener clusters visualmente atractivos: conservar este resultado negativo es parte del control analítico.

## Uso en QGIS

`segment_local_moran.csv` se une a la capa de segmentos mediante `segment_id` o la pareja `(km_inicio, km_fin)`. Para una vista conservadora debe simbolizarse `lisa_cluster_fdr`, no el cuadrante sin significancia.

La leyenda debe mantener visible **SIMULATED DEMO**.

## Interpretación limitada

- Moran I y Geary C responden si el patrón completo difiere de una distribución espacial aleatoria bajo los pesos declarados.
- LISA identifica asociaciones locales y outliers espaciales, no causas.
- FDR reduce falsos positivos, pero no convierte la simulación en evidencia.
- La geometría lineal simplifica la realidad: no representa caminos alternativos, tiempos de viaje ni conectividad operacional.

La Fase 3B abordará regímenes longitudinales como problema separado, con selección de parámetros y estabilidad explícitas.
