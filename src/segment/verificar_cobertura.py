"""Verifica cobertura OSM midiendo distancia perpendicular punto-a-linea,
no punto-a-vertice. Identifica ademas que vias forman el corredor."""

import csv, json, math
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
GJ = json.load(open(RAIZ / "data" / "raw" / "osm_candidatos.geojson", encoding="utf-8"))
PC = list(csv.DictReader(open(RAIZ / "data" / "raw" / "puntos_control.csv", encoding="utf-8")))

LAT_REF = -29.1
MX = 111320 * math.cos(math.radians(LAT_REF))
MY = 110540


def xy(lon, lat):
    return lon * MX, lat * MY


def d_seg(p, a, b):
    """Distancia de p al segmento ab, en metros."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


print(f"{'km':>6} {'vertice':>9} {'linea':>9}  via")
print("-" * 66)
usadas, ok = {}, 0
for r in PC:
    km, p = float(r["progresiva_km"]), xy(float(r["lon"]), float(r["lat"]))
    mejor_v, mejor_l, mf = float("inf"), float("inf"), None
    for f in GJ["features"]:
        c = [xy(x, y) for x, y in f["geometry"]["coordinates"]]
        for v in c:
            mejor_v = min(mejor_v, math.hypot(p[0] - v[0], p[1] - v[1]))
        for a, b in zip(c, c[1:]):
            d = d_seg(p, a, b)
            if d < mejor_l:
                mejor_l, mf = d, f
    pr = mf["properties"]
    usadas.setdefault(pr["osm_id"], pr)
    ok += mejor_l < 100
    nom = pr["nombre"] or "(sin nombre)"
    print(f"{km:>6.0f} {mejor_v:>9.0f} {mejor_l:>9.0f}  {nom[:38]} / {pr['highway']}")

print("-" * 66)
print(f"\nPuntos sobre la linea (<100 m): {ok} de {len(PC)}")
print(f"Vias distintas tocadas por los puntos de control: {len(usadas)}\n")
for oid, pr in usadas.items():
    print(f"  {oid}  {pr['nombre'] or '(sin nombre)':<40} {pr['highway']}")
