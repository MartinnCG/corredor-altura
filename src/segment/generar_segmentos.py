"""Calibra la progresiva de la traza contra los carteles de kilometraje
y genera la tabla maestra de segmentos de 1 km.

La longitud recorrida sobre la traza no coincide con la progresiva
senalizada: la traza sigue cada curva mientras el cartel mide sobre el
eje de proyecto. Se corrige interpolando linealmente entre puntos de
control, de modo que el km N del sistema sea el km N del cartel.
"""

import csv, json, math
from pathlib import Path

from shapely.geometry import LineString, Point, mapping

RAIZ = Path(__file__).resolve().parents[2]
TRAZA = json.load(open(RAIZ / "data" / "raw" / "traza_corredor.geojson", encoding="utf-8"))
PC = list(csv.DictReader(open(RAIZ / "data" / "raw" / "puntos_control.csv", encoding="utf-8")))
OUT_SEG = RAIZ / "data" / "processed" / "segmentos.csv"
OUT_GEO = RAIZ / "data" / "processed" / "segmentos.geojson"

LAT_REF = -29.1
MX = 111320 * math.cos(math.radians(LAT_REF))
MY = 110540
PASO_KM = 1.0


def xy(lon, lat):
    return lon * MX, lat * MY


def lonlat(x, y):
    return x / MX, y / MY


coords_ll = TRAZA["geometry"]["coordinates"]
traza = LineString([xy(x, y) for x, y in coords_ll])

# --- tabla de calibracion: s recorrido sobre traza <-> km senalizado ---
PC.sort(key=lambda r: float(r["progresiva_km"]))
cal = []
for r in PC:
    p = Point(*xy(float(r["lon"]), float(r["lat"])))
    cal.append((traza.project(p) / 1000, float(r["progresiva_km"])))

# monotonia: descartar anclas que rompan el orden
limpio = [cal[0]]
for s, km in cal[1:]:
    if s > limpio[-1][0] and km > limpio[-1][1]:
        limpio.append((s, km))
descartadas = len(cal) - len(limpio)
cal = limpio

print("Calibracion progresiva\n")
print(f"{'km cartel':>10} {'s traza':>10} {'factor':>9}")
print("-" * 32)
for i, (s, km) in enumerate(cal):
    f = "" if i == 0 else f"{(s - cal[i-1][0]) / (km - cal[i-1][1]):>9.3f}"
    print(f"{km:>10.0f} {s:>10.2f} {f}")
print("-" * 32)
if descartadas:
    print(f"\nAnclas descartadas por no monotonia: {descartadas}")


def km_a_s(km):
    """Progresiva senalizada -> distancia recorrida sobre la traza, en km."""
    if km <= cal[0][1]:
        return cal[0][0]
    for (s0, k0), (s1, k1) in zip(cal, cal[1:]):
        if k0 <= km <= k1:
            return s0 + (km - k0) * (s1 - s0) / (k1 - k0)
    (s0, k0), (s1, k1) = cal[-2], cal[-1]
    return s1 + (km - k1) * (s1 - s0) / (k1 - k0)


km_max = cal[-1][1]
n = int(km_max // PASO_KM)
print(f"\nSegmentos a generar: {n} de {PASO_KM:.0f} km, de km 0 a km {n}\n")

filas, features = [], []
for i in range(n):
    km_ini, km_fin = i * PASO_KM, (i + 1) * PASO_KM
    s_ini, s_fin = km_a_s(km_ini) * 1000, km_a_s(km_fin) * 1000
    s_ini = max(0, min(s_ini, traza.length))
    s_fin = max(0, min(s_fin, traza.length))
    if s_fin <= s_ini:
        continue

    a, b = traza.interpolate(s_ini), traza.interpolate(s_fin)
    medio = traza.interpolate((s_ini + s_fin) / 2)
    lon_a, lat_a = lonlat(a.x, a.y)
    lon_b, lat_b = lonlat(b.x, b.y)
    lon_m, lat_m = lonlat(medio.x, medio.y)

    filas.append({
        "segmento_id": f"S{i:04d}",
        "km_inicio": f"{km_ini:.0f}",
        "km_fin": f"{km_fin:.0f}",
        "lat_centro": f"{lat_m:.6f}",
        "lon_centro": f"{lon_m:.6f}",
        "lat_inicio": f"{lat_a:.6f}",
        "lon_inicio": f"{lon_a:.6f}",
        "lat_fin": f"{lat_b:.6f}",
        "lon_fin": f"{lon_b:.6f}",
        "long_traza_m": f"{s_fin - s_ini:.0f}",
        "fuente": "openstreetmap+puntos_control",
    })

    sub = []
    d = s_ini
    while d < s_fin:
        p = traza.interpolate(d)
        sub.append(list(lonlat(p.x, p.y)))
        d += 100
    sub.append([lon_b, lat_b])
    features.append({
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": sub},
        "properties": {"segmento_id": f"S{i:04d}", "km_inicio": km_ini, "km_fin": km_fin},
    })

OUT_SEG.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_SEG, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
    w.writeheader()
    w.writerows(filas)

OUT_GEO.write_text(json.dumps(
    {"type": "FeatureCollection", "features": features}, ensure_ascii=False),
    encoding="utf-8")

print(f"Segmentos generados: {len(filas)}")
print(f"  {OUT_SEG}")
print(f"  {OUT_GEO}\n")

print("Verificacion: progresiva calibrada de cada cartel\n")
print(f"{'km cartel':>10} {'km calibrado':>13} {'error m':>9}")
print("-" * 35)
err = []
for r in PC:
    p = Point(*xy(float(r["lon"]), float(r["lat"])))
    s = traza.project(p) / 1000
    lo, hi = 0.0, km_max
    for _ in range(60):
        mid = (lo + hi) / 2
        if km_a_s(mid) < s:
            lo = mid
        else:
            hi = mid
    kmc = (lo + hi) / 2
    e = (kmc - float(r["progresiva_km"])) * 1000
    err.append(abs(e))
    print(f"{float(r['progresiva_km']):>10.0f} {kmc:>13.3f} {e:>+9.0f}")
print("-" * 35)
print(f"\nError medio: {sum(err)/len(err):.0f} m   Error maximo: {max(err):.0f} m")
