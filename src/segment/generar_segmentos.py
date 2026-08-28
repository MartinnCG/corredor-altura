"""Genera segmentos de 1 km sobre la traza validada.

Criterio de calibracion:
- Usa como anclas duras SOLO puntos_control con confianza == "alta".
- Los puntos de confianza media (por ejemplo referencias operativas) se
  conservan en el CSV original, pero NO deforman la progresiva kilometraje.
- Interpola linealmente entre anclas de alta confianza.
"""

import csv
import json
import math
from pathlib import Path

from shapely.geometry import Point, LineString, mapping

RAIZ = Path(__file__).resolve().parents[2]

TRAZA_FILE = RAIZ / "data" / "raw" / "traza_corredor.geojson"
PC_FILE = RAIZ / "data" / "raw" / "puntos_control.csv"

OUT_CSV = RAIZ / "data" / "processed" / "segmentos.csv"
OUT_GEOJSON = RAIZ / "data" / "processed" / "segmentos.geojson"

LAT_REF = -29.1
MX = 111320 * math.cos(math.radians(LAT_REF))
MY = 110540

PASO_SEGMENTO_KM = 1.0
MUESTREO_M = 100.0


def xy(lon, lat):
    return lon * MX, lat * MY


def lonlat(x, y):
    return x / MX, y / MY


def cargar_traza():
    with open(TRAZA_FILE, encoding="utf-8") as f:
        gj = json.load(f)

    # Admite Feature o FeatureCollection
    if gj.get("type") == "Feature":
        geom = gj["geometry"]
    elif gj.get("type") == "FeatureCollection":
        if not gj.get("features"):
            raise SystemExit("ERROR: traza_corredor.geojson no contiene features.")
        geom = gj["features"][0]["geometry"]
    else:
        raise SystemExit("ERROR: formato GeoJSON de traza no reconocido.")

    if geom.get("type") != "LineString":
        raise SystemExit("ERROR: la traza debe ser LineString.")

    coords_ll = geom["coordinates"]
    coords_xy = [xy(lon, lat) for lon, lat in coords_ll]
    return LineString(coords_xy)


def cargar_puntos_control():
    with open(PC_FILE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        r["progresiva_km"] = float(r["progresiva_km"])
        r["lat"] = float(r["lat"])
        r["lon"] = float(r["lon"])
        r["confianza"] = (r.get("confianza") or "").strip().lower()

    rows.sort(key=lambda r: r["progresiva_km"])
    return rows


def construir_anclas(traza, puntos):
    anclas = []

    for r in puntos:
        if r["confianza"] != "alta":
            continue

        p = Point(*xy(r["lon"], r["lat"]))
        s_km = traza.project(p) / 1000.0
        lateral_m = traza.distance(p)

        anclas.append({
            "km": r["progresiva_km"],
            "s_km": s_km,
            "lateral_m": lateral_m,
            "observacion": r.get("observacion", ""),
        })

    if len(anclas) < 2:
        raise SystemExit("ERROR: se necesitan al menos dos puntos de confianza alta.")

    # Comprobar monotonicidad de s respecto a km
    for a, b in zip(anclas, anclas[1:]):
        if b["s_km"] <= a["s_km"]:
            raise SystemExit(
                f"ERROR: anclas no monotonicas entre km {a['km']:.0f} y {b['km']:.0f}."
            )

    return anclas


def km_a_s(km, anclas):
    """Convierte progresiva oficial km -> distancia sobre traza en km."""

    if km < anclas[0]["km"] or km > anclas[-1]["km"]:
        raise ValueError(
            f"km {km} fuera del rango calibrado "
            f"{anclas[0]['km']}..{anclas[-1]['km']}"
        )

    for a, b in zip(anclas, anclas[1:]):
        if a["km"] <= km <= b["km"]:
            if b["km"] == a["km"]:
                return a["s_km"]

            t = (km - a["km"]) / (b["km"] - a["km"])
            return a["s_km"] + t * (b["s_km"] - a["s_km"])

    # Solo por seguridad numerica
    return anclas[-1]["s_km"]


def extraer_sublinea(traza, s0_m, s1_m, paso_m=100.0):
    """Extrae una LineString entre dos distancias de la traza por muestreo."""

    if s1_m <= s0_m:
        raise ValueError("s1 debe ser mayor que s0.")

    coords = []
    s = s0_m

    while s < s1_m:
        p = traza.interpolate(s)
        coords.append((p.x, p.y))
        s += paso_m

    p = traza.interpolate(s1_m)
    coords.append((p.x, p.y))

    # Evitar geometria degenerada
    if len(coords) < 2:
        p0 = traza.interpolate(s0_m)
        p1 = traza.interpolate(s1_m)
        coords = [(p0.x, p0.y), (p1.x, p1.y)]

    return LineString(coords)


# ---------------------------------------------------------------------
# EJECUCION
# ---------------------------------------------------------------------

traza = cargar_traza()
puntos = cargar_puntos_control()
anclas = construir_anclas(traza, puntos)

print("\n=== GENERACION DE SEGMENTOS CALIBRADOS ===\n")
print("Anclas usadas: SOLO confianza alta\n")
print(f"{'km':>6} {'s_traza':>10} {'dist':>9}")
print("-" * 29)

for a in anclas:
    print(f"{a['km']:>6.0f} {a['s_km']:>10.2f} {a['lateral_m']:>7.1f} m")

print("\nPuntos excluidos de la calibracion:\n")
for r in puntos:
    if r["confianza"] != "alta":
        print(
            f"km {r['progresiva_km']:.0f} | confianza={r['confianza']} | "
            f"{r.get('observacion','')}"
        )

km_min = int(math.ceil(anclas[0]["km"]))
km_max = int(math.floor(anclas[-1]["km"]))

features = []
rows_csv = []

print("\nSegmentos:\n")
print(f"{'km':>9} {'longitud':>11} {'factor':>8}")
print("-" * 32)

for km0 in range(km_min, km_max):
    km1 = km0 + 1

    s0_km = km_a_s(float(km0), anclas)
    s1_km = km_a_s(float(km1), anclas)

    s0_m = s0_km * 1000.0
    s1_m = s1_km * 1000.0

    sub_xy = extraer_sublinea(traza, s0_m, s1_m, MUESTREO_M)
    longitud_km = sub_xy.length / 1000.0
    factor = longitud_km / (km1 - km0)

    sub_ll = LineString([lonlat(x, y) for x, y in sub_xy.coords])

    props = {
        "km_inicio": km0,
        "km_fin": km1,
        "s_inicio_km": round(s0_km, 6),
        "s_fin_km": round(s1_km, 6),
        "longitud_traza_km": round(longitud_km, 6),
        "factor_local": round(factor, 6),
        "metodo_calibracion": "solo_puntos_confianza_alta",
    }

    features.append({
        "type": "Feature",
        "geometry": mapping(sub_ll),
        "properties": props,
    })

    rows_csv.append(props)

    # Mostrar solo factores llamativos y tramos de interes
    if (
        factor < 0.90
        or factor > 1.10
        or 45 <= km0 <= 59
        or 108 <= km0 <= 116
    ):
        print(
            f"{km0:>4}->{km1:<4} "
            f"{longitud_km:>8.3f} km "
            f"{factor:>8.3f}"
        )

OUT_GEOJSON.parent.mkdir(parents=True, exist_ok=True)

with open(OUT_GEOJSON, "w", encoding="utf-8") as f:
    json.dump({
        "type": "FeatureCollection",
        "features": features,
    }, f, ensure_ascii=False)

with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "km_inicio",
            "km_fin",
            "s_inicio_km",
            "s_fin_km",
            "longitud_traza_km",
            "factor_local",
            "metodo_calibracion",
        ],
    )
    writer.writeheader()
    writer.writerows(rows_csv)

print("\nResultado:")
print(f"Segmentos generados: {len(features)}")
print(f"Rango: km {km_min} -> {km_max}")
print(f"\nGuardado:\n{OUT_CSV}\n{OUT_GEOJSON}")
