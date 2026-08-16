# Diccionario de datos

## Convenciones generales

- Coordenadas en grados decimales, EPSG:4326. Latitud y longitud negativas.
- Progresivas en kilometros desde el km 0 del corredor (Garita Guandacol).
- Fechas en formato ISO: AAAA-MM-DD.
- Toda fila lleva campo `fuente`. Sin fuente declarada, el dato no entra.
- Campos vacios significan "pendiente de relevar", no cero.

## Campo `fuente` - valores admitidos

| Valor | Significado |
|---|---|
| `foto_gps_campo` | Fotografia georreferenciada tomada en terreno |
| `informante_campo` | Descripcion verbal de personal que opera el corredor |
| `google_earth` | Medicion sobre modelo de elevacion de Google Earth |
| `observacion_fotografica` | Inferido de fotografia, no declarado por informante |
| `ni43101_vicuna_2026` | Reporte tecnico NI 43-101, Lundin Mining, 16/02/2026 |
| `era5` / `ign_ar` / `sentinel2` | Fuentes de datos publicas procesadas |

## Campo `confianza`

| Valor | Criterio |
|---|---|
| `alta` | Progresiva leida directamente de cartel de kilometraje en foto |
| `media` | Progresiva inferida de cartel de nombre de tramo o descripcion |
| `baja` | Estimada por interpolacion |

## Tablas

### puntos_control.csv
Correspondencia entre progresiva y coordenada. Es la tabla que calibra la
referenciacion lineal de todo el sistema.

### elevaciones_referencia.csv
Elevaciones medidas puntualmente. Sirven para validar el modelo digital de
elevaciones descargado, no para reemplazarlo.

### tramos_operativos.csv
Como nombra los tramos el personal que opera el corredor.

### zonas_falla.csv
Modos de falla dominantes por tramo, segun informante de campo.
NOTA METODOLOGICA: los limites de las zonas de falla NO coinciden con los
limites de los tramos operativos. Esa discordancia es un resultado del
trabajo, no un error a corregir.

### puntos_singulares.csv
Elementos fijos del corredor: cruces de rio, cargaderos, garitas,
campamentos, divisiones de camino, pasos y salinas.

### velocidades_senalizadas.csv
Velocidad maxima senalizada. Es riesgo ya evaluado por el operador y sirve
como variable de contraste independiente contra el indice modelado.
