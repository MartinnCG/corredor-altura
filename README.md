# Corredor de Altura

Modelo geoespacial de **exposición relativa por segmento** aplicado al Corredor Este de acceso al Proyecto Vicuña, entre La Rioja y San Juan, Argentina.

**Cobertura analítica validada:** km 0-130
**Unidad de análisis:** 130 segmentos operacionales de 1 km
**Estado:** pipeline analítico v1 completado

---

## Objetivo

Construir una representación cuantitativa, reproducible y trazable del corredor que permita caracterizar las condiciones topográficas, hidrológicas y climáticas asociadas a cada segmento de 1 km.

El producto analítico principal es un **Índice de Exposición por Segmento**, diseñado para comparar la exposición relativa entre sectores del mismo corredor.

El índice **no representa riesgo absoluto** y no predice fallas, accidentes, cierres ni necesidad de mantenimiento.

---

## Arquitectura analítica

El proyecto sigue una secuencia reproducible:

**Fuentes -> Referenciación espacial -> Segmentación -> Variables -> Dataset maestro -> Índice -> Validación -> Producto GIS**

La progresiva operacional constituye la referencia común que permite integrar información proveniente de distintas fuentes sobre los mismos 130 segmentos.

---

## 1. Referencia espacial y segmentación

La traza fue reconstruida utilizando conectividad de la red vial de OpenStreetMap y puntos GPS de control obtenidos en campo.

Los puntos de control se proyectan sobre las aristas de la red y los puntos clasificados con **confianza alta** funcionan como anclas de calibración de la progresiva.

Resultado:

- corredor validado visualmente en QGIS sobre imagen satelital;
- cobertura analítica km 0-130;
- 130 segmentos de 1 km;
- corrección de anomalías geométricas detectadas durante la validación;
- referencias de confianza media conservadas como información operacional, pero excluidas como anclas duras de calibración.

El sector posterior al km 130 queda fuera de la base analítica v1 por no disponer de continuidad cartográfica y ancla de campo de alta confianza suficientes.

---

## 2. Fuentes de información

| Componente | Fuente | Aplicación |
|---|---|---|
| Red vial | OpenStreetMap | Reconstrucción de la traza |
| Control espacial | GPS de campo | Calibración y validación |
| Elevación | IGN Argentina - MDE-Ar v2.1 | Altitud y variables topográficas |
| Hidrología | MDE-Ar v2.1 | Dirección, acumulación y red de drenaje |
| Clima | ERA5-Land / Copernicus ARCO | Climatología histórica |
| Evidencia operacional | IPER y relevamiento de campo | Validación independiente |
| Contexto | Documentación pública del Proyecto Vicuña | Contextualización del caso |

---

## 3. Topografía

Se utilizó el **MDE-Ar v2.1 de IGN Argentina**, con resolución aproximada de 30 m.

A partir del DEM se derivaron variables de elevación, pendiente longitudinal y pendiente del terreno alrededor de cada segmento.

La elevación del DEM fue contrastada contra referencias independientes:

- MAE: 2.88 m
- RMSE: 3.53 m
- sesgo medio: -0.58 m
- error absoluto máximo: 7.64 m

Los resultados no justificaron aplicar una corrección vertical adicional.

---

## 4. Hidrología

El análisis hidrológico utiliza el DEM reproyectado a **EPSG:32719 (UTM 19S)**.

Pipeline:

1. acondicionamiento del DEM;
2. resolución de depresiones y zonas planas;
3. dirección de flujo D8;
4. acumulación de flujo;
5. extracción de redes de drenaje;
6. resumen de exposición por segmento.

Umbrales utilizados:

- drenaje secundario: >= 2500 celdas;
- drenaje principal: >= 10000 celdas;
- buffer de análisis alrededor del segmento: 50 m.

---

## 5. Clima

La climatología se construyó con **ERA5-Land mediante Copernicus ARCO**.

Periodo analizado:

**01/01/2001 - 31/12/2025**

Esto proporciona 25 años completos de información climática horaria.

La información fue procesada a nivel de celda y posteriormente asignada a los segmentos del corredor.

Resultado:

- 77 celdas climáticas procesadas;
- 12 variables climáticas derivadas;
- 130 segmentos con cobertura;
- 0 valores faltantes.

---

## 6. Dataset analítico maestro

Las distintas familias de variables se consolidan en:

`data/processed/features_segmentos_master.csv`

Dimensiones:

- 130 filas;
- 46 columnas;
- 44 variables numéricas;
- 0 valores faltantes.

Este dataset constituye la base reproducible utilizada para construir el índice de exposición.

---

## 7. Índice de Exposición por Segmento

El modelo v1 utiliza siete variables organizadas en tres dimensiones.

### Topografía

- `pendiente_media_abs_pct`
- `pendiente_terreno_p90_pct`

### Hidrología

- `n_drenajes_principales_50m`
- `area_aportante_max_50m_km2`

Para el área aportante se aplica transformación `log1p` antes de la normalización para reducir la influencia de valores extremos.

### Clima

- `precipitacion_diaria_p95_mm`
- `viento_p95_ms`
- `fraccion_horas_nieve_ge50pct`

Las variables son normalizadas y combinadas en subíndices. Cada dimensión recibe el mismo peso: **Topografía 1/3, Hidrología 1/3 y Clima 1/3**.

El índice final se expresa en una escala relativa. Los 130 segmentos se clasifican mediante quintiles en: Muy baja, Baja, Media, Alta y Muy alta.

Estas clases describen **exposición relativa dentro del corredor estudiado** y no categorías universales de riesgo.

---

## 8. Validación

La validación utiliza evidencia operacional estructurada de manera independiente del cálculo del índice.

Archivo: `data/processed/validacion_indice_exposicion.csv`

La evidencia incluye información proveniente del IPER del camino y del relevamiento de campo. El objetivo es evaluar **coherencia e interpretabilidad** entre el patrón cuantitativo de exposición y las condiciones operacionales documentadas.

La validación no constituye prueba causal ni demuestra capacidad predictiva sobre fallas o accidentes.

---

## 9. Productos principales

### Datos

- `data/processed/segmentos.csv`
- `data/processed/segmentos.geojson`
- `data/processed/features_segmentos_master.csv`
- `data/processed/indice_exposicion_segmentos.csv`
- `data/processed/segmentos_indice_exposicion.geojson`
- `data/processed/validacion_indice_exposicion.csv`

### Productos visuales

- `outputs/figuras/perfil_longitudinal_indice_exposicion.png`
- `outputs/figuras/mapa_indice_exposicion.qgz`
- `outputs/mapa_indice_exposicion_corredor_0_130.pdf`

---

## 10. Estructura del repositorio

- `config/`: configuración general del caso de estudio.
- `data/raw/`: datos originales y evidencia de entrada.
- `data/interim/`: productos intermedios regenerables.
- `data/external/`: fuentes externas pesadas no versionadas.
- `data/processed/`: datasets analíticos y capas finales.
- `src/ingest/`: adquisición de fuentes.
- `src/segment/`: construcción de traza y segmentación.
- `src/features/`: ingeniería de variables, índice y validación.
- `docs/`: documentación técnica y académica.
- `outputs/`: mapas, figuras y entregables.

## 11. Trazabilidad y reproducibilidad

La lógica analítica se mantiene en scripts versionados dentro de `src/`. El pipeline incluye reconstrucción de traza, segmentación, procesamiento y validación del DEM, topografía, hidrología, climatología ERA5-Land, consolidación del dataset maestro, cálculo del índice, validación operacional y generación de productos espaciales.

`config/corredor.yml` documenta el alcance, las fuentes y los parámetros generales del caso de estudio. Git registra la evolución metodológica y los principales hitos del pipeline.

Los rásteres derivados y fuentes externas pesadas pueden regenerarse mediante los scripts correspondientes y no necesitan mantenerse bajo control de versiones.

---

## 12. Stack

- Python 3.11+
- pandas y numpy
- scipy
- geopandas y shapely
- rasterio y rioxarray
- pyproj
- pysheds
- xarray y zarr
- QGIS
- Git

---

## 13. Limitaciones

- El índice representa **exposición relativa**, no riesgo absoluto.
- No existe una variable objetivo suficiente para entrenar o validar un modelo predictivo de fallas.
- El índice no estima probabilidad de accidente, cierre o deterioro.
- ERA5-Land posee una resolución espacial más gruesa que la unidad de análisis de 1 km.
- La resolución del DEM limita el detalle de procesos topográficos e hidrológicos locales.
- La evidencia operacional disponible no posee cobertura homogénea en todo el corredor.
- La cobertura analítica validada termina en km 130.
- El sector posterior al km 130 requiere nueva evidencia espacial y de campo antes de incorporarse al modelo.

---

## 14. Estado del proyecto

| Componente | Estado |
|---|---|
| Construcción y validación de traza | Completado |
| Segmentación km 0-130 | Completado |
| Variables topográficas | Completado |
| Variables hidrológicas | Completado |
| Variables climáticas | Completado |
| Dataset maestro | Completado |
| Índice de exposición v1 | Completado |
| Validación operacional v1 | Completado |
| Capa GIS del índice | Completado |
| Mapa cartográfico | Completado |
| Documentación y reproducibilidad | En cierre |
| Dashboard interactivo | Pendiente |

---

## Próxima etapa

La siguiente etapa funcional consiste en construir un **dashboard interactivo mínimo** sobre los productos analíticos existentes.

El dashboard no recalculará el modelo. Consumirá los resultados versionados para explorar el índice y clase de exposición por segmento, los subíndices de topografía, hidrología y clima, el perfil longitudinal, la ubicación espacial y las variables que explican la exposición observada.

El objetivo es transformar el pipeline analítico validado en un producto de consulta reproducible, interpretable y presentable.
