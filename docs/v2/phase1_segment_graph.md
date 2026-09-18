# V2 — Fase 1: identidad y grafo de segmentos

## Propósito

La Fase 1 representa la continuidad longitudinal del corredor km 0–130 como un grafo lineal auditable. Usa las claves congeladas de `data/processed/segmentos.csv` y no modifica ningún producto V1.

Esta base permitirá, en fases posteriores, calcular contexto espacial, autocorrelación, regímenes contiguos y propagación de evidencia sin confundir vecindad física con similitud estadística.

## Identidad

La clave fuente continúa siendo `(km_inicio, km_fin)`. El identificador V2 se deriva de forma determinista:

```text
(0, 1)     -> seg_000_001
(57, 58)   -> seg_057_058
(129, 130) -> seg_129_130
```

El identificador no se escribe dentro de las tablas V1.

## Grafo v0.1

- 130 nodos: uno por segmento de un kilómetro.
- 129 relaciones físicas no dirigidas.
- 258 aristas en el CSV dirigido, una en cada sentido.
- Vecindad de primer orden exclusivamente.
- Peso bruto `1.0`; cualquier normalización pertenece al análisis que lo consuma.
- Los segmentos extremos tienen grado 1 y los interiores grado 2.

Producto:

```text
data/processed/v2/segment_neighbors.csv
```

## Reproducción

Desde la raíz del repositorio:

```bash
python src/segment/generar_grafo_segmentos_v2.py
python src/segment/generar_grafo_segmentos_v2.py --check
python -m unittest discover -s tests -v
```

`--check` no escribe archivos: regenera el contenido en memoria y falla si el producto versionado difiere.

## Uso en QGIS

`segment_neighbors.csv` puede cargarse como tabla sin geometría. Las columnas `km_inicio` y `km_fin` permiten relacionar cada arista con `segmentos.geojson`; las columnas `neighbor_km_inicio` y `neighbor_km_fin` identifican el segmento contiguo.

El archivo expresa topología, no distancia euclidiana, accesibilidad, similitud ni causalidad.

## Controles implementados

- cobertura exacta y ordenada km 0–130;
- identidad determinista y única;
- ausencia de autoaristas y duplicados;
- reciprocidad de todas las aristas;
- grado correcto de extremos e interiores;
- conectividad completa de la cadena;
- regeneración byte a byte del producto;
- hashes SHA-256 de los cuatro productos canónicos V1.

## Fuera de alcance

- estadística de Moran o Geary;
- clusters locales;
- regímenes espaciales;
- snapshots temporales;
- eventos de cambio;
- priorización;
- datos simulados u observados nuevos.

Estas capacidades requieren PRs separados y usarán este grafo como dependencia validada.
