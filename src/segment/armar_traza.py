"""Ensambla la traza continua del corredor a partir de las vias OSM.

No usa grafo ni conectividad topologica: OSM tiene el camino partido en
tramos que no se tocan. En su lugar construye una poligonal de referencia
con los puntos de control, filtra las vias cercanas, y ordena sus vertices
por progresiva sobre esa poligonal.
"""

import csv, json, math
from pathlib import Path

from shapely.geometry import LineString, Point, mapping

RAIZ = Path(__file__).resolve().parents[2]
GJ = json.load(open(RAIZ / "data" / "raw" / "osm_candidatos.geojson", encoding="utf-8"))
PC = list(csv.DictReader(open(RAIZ / "data" / "raw" / "puntos_control.csv", encoding="utf-8")))
SALIDA = RAIZ / "data" / "raw" / "traza_corredor.geojson"

BUFFER_M = 600      # distancia maxima de un vertice a la poligonal de referencia
COBERTURA_MIN = 0.02 # fraccion de vertices de una via que debe caer dentro del buffer
BIN_M = 50          # resolucion de muestreo a lo largo del corredor

LAT_REF = -29.1
MX = 111320 * math.cos(math.radians(LAT_REF))
MY = 110540


def xy(lon, lat):
    return lon * MX, lat * MY


def lonlat(x, y):
    return x / MX, y / MY


# --- 1. poligonal de referencia a partir de los puntos de control -----
PC.sort(key=lambda r: float(r["progresiva_km"]))
ref_pts = [xy(float(r["lon"]), float(r["lat"])) for r in PC]
ref = LineString(ref_pts)
print(f"Poligonal de referencia: {len(ref_pts)} puntos de control, "
      f"{ref.length/1000:.1f} km en linea quebrada\n")

# --- 2. filtrar vias cercanas a la referencia ------------------------
retenidas = []
for f in GJ["features"]:
    c = [xy(x, y) for x, y in f["geometry"]["coordinates"]]
    if len(c) < 2:
        continue
    dentro = sum(1 for p in c if ref.distance(Point(p)) < BUFFER_M)
    if dentro / len(c) >= COBERTURA_MIN:
        retenidas.append((f["properties"], c))

print(f"Vias OSM totales:    {len(GJ['features'])}")
print(f"Vias retenidas:      {len(retenidas)}\n")

if not retenidas:
    raise SystemExit("Ninguna via cerca de la referencia. Revisar BUFFER_M.")

# --- 3. proyectar vertices y quedarse con el mejor por bin -----------
bins = {}
for props, c in retenidas:
    for p in c:
        pt = Point(p)
        d = ref.distance(pt)
        if d >= BUFFER_M:
            continue
        s = ref.project(pt)
        k = int(s // BIN_M)
        if k not in bins or d < bins[k][1]:
            bins[k] = (p, d, props.get("nombre", ""))

if len(bins) < 2:
    raise SystemExit("Muy pocos puntos. Revisar parametros.")

coords_xy = [bins[k][0] for k in sorted(bins)]
traza_xy = LineString(coords_xy)
traza_ll = LineString([lonlat(x, y) for x, y in coords_xy])

huecos = [(a, b) for a, b in zip(sorted(bins), sorted(bins)[1:]) if b - a > 3]
print(f"Vertices de la traza: {len(coords_xy)}")
print(f"Longitud ensamblada:  {traza_xy.length/1000:.1f} km")
if huecos:
    print(f"Huecos detectados:    {len(huecos)} "
          f"(el mayor de {max(b-a for a,b in huecos)*BIN_M/1000:.1f} km)")
print()

# --- 4. verificacion contra los carteles -----------------------------
print(f"{'km cartel':>10} {'km calculado':>13} {'error':>9} {'desvio lat':>11}")
print("-" * 48)
errores = []
for r in PC:
    p = Point(*xy(float(r["lon"]), float(r["lat"])))
    km_calc = traza_xy.project(p) / 1000
    km_real = float(r["progresiva_km"])
    err = km_calc - km_real
    errores.append(abs(err))
    print(f"{km_real:>10.0f} {km_calc:>13.2f} {err:>+9.2f} "
          f"{traza_xy.distance(p):>10.0f} m")

print("-" * 48)
print(f"\nError absoluto medio: {sum(errores)/len(errores):.2f} km")
print(f"Error maximo:         {max(errores):.2f} km")

# --- 5. guardar ------------------------------------------------------
SALIDA.write_text(json.dumps({
    "type": "Feature",
    "geometry": mapping(traza_ll),
    "properties": {
        "fuente": "openstreetmap",
        "metodo": "proyeccion sobre poligonal de puntos de control",
        "vertices": len(coords_xy),
        "longitud_km": round(traza_xy.length / 1000, 2),
    },
}, ensure_ascii=False), encoding="utf-8")
print(f"\nGuardado en {SALIDA}")
