# Corredor de Altura

Modelo de indicadores de riesgo por tramo para corredores viales mineros.

Caso de aplicacion: corredor de acceso este al Proyecto Vicuna, entrada por
Garita Guandacol, La Rioja, Argentina. Km 0 a 140.

---

## Principio de arquitectura

**Construir generico, aplicar particular.**

Ningun nombre de corredor, coordenada o umbral va escrito en el codigo.
Todo entra por `config/corredor.yml`. Para aplicar el sistema a otro
corredor se escribe otro archivo de configuracion, no se toca el codigo.

Si una funcion necesita saber que el corredor se llama Vicuna, esa funcion
esta mal escrita.

---

## Estructura

```
corredor-altura/
├── config/
│   └── corredor.yml          Definicion del corredor. Unico lugar con datos particulares.
├── data/
│   ├── raw/                  Datos crudos. NUNCA se modifican a mano despues de cargados.
│   ├── interim/              Intermedios del procesamiento. Descartables y regenerables.
│   └── processed/            Tablas finales listas para analisis.
├── notebooks/                Exploracion. No contienen logica de produccion.
├── src/
│   ├── ingest/               Conectores a fuentes. Un modulo por fuente.
│   ├── segment/              Segmentacion y referenciacion lineal.
│   ├── features/             Construccion de variables derivadas.
│   └── indicators/           Calculo del indice de riesgo.
├── docs/
│   └── diccionario_datos.md  Definicion de cada tabla y campo.
└── outputs/                  Entregables: tablero, figuras, informe.
```

### Reglas de las carpetas de datos

- `raw/` es de solo lectura una vez cargado. Un dato mal cargado se corrige
  en el archivo original y se vuelve a cargar, nunca se edita en el medio.
- `interim/` se puede borrar entero y regenerar corriendo el pipeline.
- `processed/` es lo unico que consumen los notebooks y el tablero.

---

## Convenciones

**Nombres de archivo y columna:** minusculas, sin tildes, separados por guion bajo.

**Progresivas:** siempre en kilometros desde el km 0 del corredor, campo
`progresiva_km`. Es la clave que une todo el sistema.

**Trazabilidad:** toda tabla lleva columna `fuente`. Sin fuente declarada,
el dato no entra al pipeline.

**Idioma:** codigo y nombres de campo en espanol sin tildes. Docstrings en
ingles cuando el modulo sea reutilizable.

---

## Estado de los datos

### Cargado

| Archivo | Contenido | Cobertura |
|---|---|---|
| `puntos_control.csv` | 8 pares progresiva-coordenada | km 0, 20, 25, 32, 35, 110, 115, 130 |
| `elevaciones_referencia.csv` | 5 elevaciones medidas | km 110 a 130 |
| `tramos_operativos.csv` | Nomenclatura de tramos | km 0 a 40 |
| `zonas_falla.csv` | Modos de falla dominantes | km 0 a 40, mas evento de nieve km 110-140 |
| `puntos_singulares.csv` | 12 elementos fijos | Parcial, varios sin coordenada |
| `velocidades_senalizadas.csv` | 3 registros | Parcial |

### Pendiente

- Traza continua del corredor (a digitalizar sobre imagen satelital)
- Modos de falla y nomenclatura km 40 a 140
- Coordenadas de cruces de rio y cargaderos del tramo bajo
- Velocidades senalizadas por tramo
- Fechas y duracion de cortes historicos

### Fuera de alcance declarado

Km 140 a 220: sin acceso verificable, tramo operado por un tercero,
intransitable por nieve en invierno. Se declara como limitacion del estudio.

---

## Hallazgos preliminares

**1. La segmentacion operativa no coincide con la de falla.**
Los tramos nombrados por el personal cortan en km 20, 26 y 32. Las zonas de
falla cortan en km 20, 25 y 35. Esa discordancia significa que el nombre
operativo no predice el riesgo, lo que justifica el trabajo.

**2. El perfil altimetrico no es monotono.**
El Paso del Leoncito (3.985 m, ~km 115) es un maximo local. El camino
desciende despues hacia Salinas del Leoncito (3.655 m, ~km 125). La
elevacion absoluta por si sola no explica la acumulacion de nieve; la forma
del terreno y la exposicion tambien intervienen.

**3. Existe un evento de validacion documentado.**
Fotografia georreferenciada del 15/08/2026 entre km 110 y 130 con nieve y
despeje mecanico. Permite contrastar el modelo contra una condicion real
con fecha y ubicacion exactas.

---

## Orden de trabajo

**Etapa 1 - Definicion y relevamiento**
1. Digitalizar la traza del corredor sobre imagen satelital, usando
   `puntos_control.csv` como control.
2. Verificar que las progresivas calculadas sobre la traza coincidan con las
   de los carteles. Tolerancia aceptable a definir y documentar.
3. Generar la tabla maestra de segmentos de 1 km.

**Etapa 2 - Construccion de la base**
4. Descargar el modelo digital de elevaciones para la caja definida en config.
5. Muestrear altitud, pendiente, exposicion y acumulacion de flujo por segmento.
6. Ingestar series climaticas y aplicar correccion por gradiente termico.
7. Procesar escenas satelitales.
8. Consolidar el modelo de datos unificado.

**Etapa 3 - Modelado**
9. Construir variables derivadas.
10. Definir y calcular el indice de riesgo por segmento.
11. Validar contra zonas de falla declaradas, velocidades senalizadas y el
    evento de nieve documentado.

**Etapa 4 - Producto**
12. Tablero, documentacion, informe y videopresentacion.

---

## Stack

- Python 3.11+
- Geoespacial: `geopandas`, `shapely`, `rasterio`, `rioxarray`, `pyproj`, `pysheds`
- Datos: `pandas`, `numpy`
- Configuracion: `pyyaml`
- SIG de escritorio: QGIS
- Base de datos: PostgreSQL con PostGIS

Todo software libre. Costo de licencias: cero.

---

## Fuentes

| Fuente | Uso | Acceso |
|---|---|---|
| Open-Meteo / ERA5 | Clima historico | Gratuito, sin clave |
| IGN Argentina | Modelo de elevaciones, capas SIG | Gratuito |
| Copernicus Data Space | Imagenes Sentinel-2 | Gratuito, con registro |
| NI 43-101 Vicuna (Lundin Mining, 16/02/2026) | Contexto del corredor | Publico |
| Relevamiento de campo | Nomenclatura, modos de falla, puntos singulares | Informante directo |

---

## Limitaciones reconocidas

**Con fuentes publicas se modela exposicion al riesgo, no se mide estado del
camino.** Sentinel-2 tiene 10 m de resolucion y un camino de ripio tiene
entre 8 y 12 m de ancho: un pixel. Permite detectar traza, nieve, humedad y
pluma de polvo. No permite detectar calamina, baches ni rugosidad.

**La resolucion climatica es gruesa.** El reanalisis global tiene celdas de
decenas de kilometros. En cordillera una celda cubre miles de metros de
desnivel. Se aplica correccion por gradiente termico vertical usando la
altitud real de cada segmento.

## Validación de traza y segmentación — 28/08/2026

Se reconstruyó la geometría del corredor utilizando conectividad de la red vial OSM entre puntos de control GPS, reemplazando el método anterior basado en selección de vértices por proximidad.

### Resultado
- Corredor validado visualmente en QGIS sobre Google Satellite: km 0–130.
- Corregido el zigzag artificial detectado entre km 50–55.
- Corregida la anomalía geométrica/calibración detectada entre km 110–115.
- Segmentos de 1 km regenerados sobre la nueva traza.
- Los puntos de control con confianza alta se utilizan como anclas de calibración.
- Las referencias operativas km 20 (La Troya) y km 32 (El Zapallar), clasificadas con confianza media, se conservan como referencias pero no intervienen como anclas duras de calibración.
- El sector inicial presenta diferencias entre distancia física de la traza y progresiva oficial; se conserva la progresiva calibrada sin alterar una geometría que fue validada visualmente.

### Archivos principales
- data/raw/traza_corredor.geojson
- data/processed/segmentos.geojson
- data/processed/segmentos.csv
- src/segment/armar_traza.py
- src/segment/generar_segmentos.py

Validación: inspección visual completa en QGIS contra imagen satelital y puntos GPS de campo.
