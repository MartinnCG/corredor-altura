"""Descarga vias candidatas desde OpenStreetMap y las contrasta
contra los puntos de control relevados en campo."""

import csv, json, math
from pathlib import Path
import requests, yaml

RAIZ = Path(__file__).resolve().parents[2]
CFG = yaml.safe_load(open(RAIZ / "config" / "corredor.yml", encoding="utf-8"))
BB = CFG["corredor"]["bbox"]
SALIDA = RAIZ / "data" / "raw" / "osm_candidatos.geojson"

QUERY = f"""[out:json][timeout:300];
way["highway"~"^(track|unclassified|service|road|residential|tertiary)$"]
({BB['lat_min']},{BB['lon_min']},{BB['lat_max']},{BB['lon_max']});
out geom;"""


def dist_m(la1, lo1, la2, lo2):
    R = 6371000
    p1, p2 = math.radians(la1), math.radians(la2)
    a = (math.sin(math.radians(la2 - la1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lo2 - lo1) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


print("Consultando Overpass API...")
r = requests.post("https://overpass-api.de/api/interpreter", data={"data": QUERY}, headers={"User-Agent": "corredor-altura/0.1 (proyecto academico)"}, timeout=300)
r.raise_for_status()

feats = []
for e in r.json().get("elements", []):
    g = e.get("geometry") or []
    if len(g) < 2:
        continue
    t = e.get("tags", {})
    feats.append({
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[p["lon"], p["lat"]] for p in g]},
        "properties": {"osm_id": e["id"], "nombre": t.get("name", ""),
                       "highway": t.get("highway", ""), "surface": t.get("surface", "")},
    })

SALIDA.parent.mkdir(parents=True, exist_ok=True)
json.dump({"type": "FeatureCollection", "features": feats},
          open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False)
print(f"Vias descargadas: {len(feats)}  ->  {SALIDA}")

with open(RAIZ / "data" / "raw" / "puntos_control.csv", encoding="utf-8") as f:
    puntos = [(float(x["progresiva_km"]), float(x["lat"]), float(x["lon"]))
              for x in csv.DictReader(f)]

print(f"\n{'km':>6} {'dist (m)':>10}  nombre / tipo")
print("-" * 60)
ok = 0
for km, la, lo in puntos:
    mejor, mf = float("inf"), None
    for f in feats:
        for lo_v, la_v in f["geometry"]["coordinates"]:
            d = dist_m(la, lo, la_v, lo_v)
            if d < mejor:
                mejor, mf = d, f
    p = mf["properties"] if mf else {}
    ok += mejor < 100
    print(f"{km:>6.0f} {mejor:>10.0f}  {p.get('nombre') or '(sin nombre)'} / {p.get('highway','')}")

print("-" * 60)
print(f"\nPuntos con via a menos de 100 m: {ok} de {len(puntos)}")
print("OSM sirve como traza base." if ok == len(puntos)
      else "Cobertura parcial: usar OSM y digitalizar los huecos." if ok >= len(puntos) * 0.6
      else "Cobertura insuficiente: digitalizar a mano en QGIS.")
