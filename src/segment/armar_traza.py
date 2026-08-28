"""Construye la traza del corredor usando la red vial OSM y snap sobre aristas.

Mejoras respecto de la version anterior:
- Los puntos de control se proyectan sobre el segmento OSM mas cercano,
  no sobre el vertice OSM mas cercano.
- Cada punto proyectado se inserta como nodo real del grafo, dividiendo
  la arista correspondiente.
- Se preserva la conectividad original de cada LineString OSM.
- Solo se cierran pequenos gaps entre extremos de vias.
"""

import csv
import json
import math
import heapq
from pathlib import Path
from collections import defaultdict

from shapely.geometry import Point, LineString, mapping

RAIZ = Path(__file__).resolve().parents[2]
OSM_FILE = RAIZ / "data" / "raw" / "osm_candidatos.geojson"
PC_FILE = RAIZ / "data" / "raw" / "puntos_control.csv"
SALIDA = RAIZ / "data" / "raw" / "traza_corredor.geojson"

LAT_REF = -29.1
MX = 111320 * math.cos(math.radians(LAT_REF))
MY = 110540

TOLERANCIA_GAP_M = 20.0
MAX_SNAP_PC_M = 250.0
ROUND_COORD = 3


def xy(lon, lat):
    return lon * MX, lat * MY


def lonlat(x, y):
    return x / MX, y / MY


def key(p):
    return (round(float(p[0]), ROUND_COORD), round(float(p[1]), ROUND_COORD))


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def add_edge(g, a, b, w=None):
    a, b = key(a), key(b)
    if a == b:
        return
    if w is None:
        w = dist(a, b)
    g[a].append((b, w))
    g[b].append((a, w))


def dijkstra(g, start, end):
    pq = [(0.0, start)]
    best = {start: 0.0}
    prev = {}

    while pq:
        cost, u = heapq.heappop(pq)
        if u == end:
            break
        if cost != best.get(u):
            continue

        for v, w in g.get(u, []):
            nc = cost + w
            if nc < best.get(v, float("inf")):
                best[v] = nc
                prev[v] = u
                heapq.heappush(pq, (nc, v))

    if end not in best:
        return None, None

    path = [end]
    while path[-1] != start:
        path.append(prev[path[-1]])
    path.reverse()
    return path, best[end]


# ---------------------------------------------------------------------
# Cargar datos
# ---------------------------------------------------------------------

with open(OSM_FILE, encoding="utf-8") as f:
    gj = json.load(f)

with open(PC_FILE, encoding="utf-8") as f:
    pcs = list(csv.DictReader(f))

pcs.sort(key=lambda r: float(r["progresiva_km"]))

# Lista de segmentos OSM reales.
# edge_id = (indice_feature, indice_segmento)
edges = []
way_endpoints = set()

for fi, feat in enumerate(gj["features"]):
    geom = feat.get("geometry", {})
    if geom.get("type") != "LineString":
        continue

    coords = geom.get("coordinates", [])
    if len(coords) < 2:
        continue

    pts = [key(xy(lon, lat)) for lon, lat in coords]
    way_endpoints.add(pts[0])
    way_endpoints.add(pts[-1])

    props = feat.get("properties", {})
    oid = props.get("osm_id")

    for si, (a, b) in enumerate(zip(pts, pts[1:])):
        if a == b:
            continue
        edges.append({
            "id": (fi, si),
            "a": a,
            "b": b,
            "line": LineString([a, b]),
            "osm_id": oid,
        })

print("\n=== ARMADO DE TRAZA: SNAP SOBRE ARISTAS OSM ===\n")
print(f"Features OSM: {len(gj['features'])}")
print(f"Segmentos OSM: {len(edges)}")
print(f"Puntos de control: {len(pcs)}")

# ---------------------------------------------------------------------
# Snap de cada PC al segmento OSM mas cercano
# ---------------------------------------------------------------------

snaps_by_edge = defaultdict(list)
anchors = []

print("\nSnap de puntos de control sobre aristas:\n")
print(f"{'km':>6} {'dist':>9} {'osm_id':>12}")
print("-" * 31)

for idx, r in enumerate(pcs):
    pxy = xy(float(r["lon"]), float(r["lat"]))
    pt = Point(pxy)

    best_edge = None
    best_d = float("inf")
    best_proj = None
    best_t = None

    for e in edges:
        d = e["line"].distance(pt)
        if d < best_d:
            s = e["line"].project(pt)
            proj = e["line"].interpolate(s)
            length = e["line"].length
            t = 0.0 if length == 0 else s / length

            best_d = d
            best_edge = e
            best_proj = key((proj.x, proj.y))
            best_t = t

    km = float(r["progresiva_km"])

    if best_d > MAX_SNAP_PC_M:
        raise SystemExit(
            f"ERROR: km {km:.0f} esta a {best_d:.1f} m de la red OSM."
        )

    snap_rec = {
        "pc_index": idx,
        "km": km,
        "node": best_proj,
        "t": best_t,
        "distance": best_d,
        "osm_id": best_edge["osm_id"],
        "edge_id": best_edge["id"],
    }

    snaps_by_edge[best_edge["id"]].append(snap_rec)
    anchors.append(snap_rec)

    print(f"{km:>6.0f} {best_d:>7.1f} m {str(best_edge['osm_id']):>12}")

# ---------------------------------------------------------------------
# Construir grafo dividiendo las aristas donde caen los PC
# ---------------------------------------------------------------------

graph = defaultdict(list)

for e in edges:
    split = [(0.0, e["a"]), (1.0, e["b"])]

    for s in snaps_by_edge.get(e["id"], []):
        split.append((s["t"], s["node"]))

    # Ordenar y eliminar nodos repetidos consecutivos
    split.sort(key=lambda x: x[0])

    ordered = []
    for t, node in split:
        node = key(node)
        if not ordered or node != ordered[-1][1]:
            ordered.append((t, node))

    for (_, a), (_, b) in zip(ordered, ordered[1:]):
        add_edge(graph, a, b)

# ---------------------------------------------------------------------
# Cerrar pequenos gaps SOLO entre extremos de ways
# ---------------------------------------------------------------------

cell = TOLERANCIA_GAP_M
grid = defaultdict(list)

for p in way_endpoints:
    grid[(int(p[0] // cell), int(p[1] // cell))].append(p)

gap_pairs = set()

for p in way_endpoints:
    ix = int(p[0] // cell)
    iy = int(p[1] // cell)

    candidates = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            candidates.extend(grid.get((ix + dx, iy + dy), []))

    nearest = None
    nearest_d = float("inf")

    for q in candidates:
        if q == p:
            continue
        d = dist(p, q)
        if 0 < d <= TOLERANCIA_GAP_M and d < nearest_d:
            nearest = q
            nearest_d = d

    if nearest is not None:
        pair = tuple(sorted((p, nearest)))
        if pair not in gap_pairs:
            add_edge(graph, p, nearest, nearest_d)
            gap_pairs.add(pair)

print(f"\nGaps OSM cerrados <= {TOLERANCIA_GAP_M:.0f} m: {len(gap_pairs)}")

# ---------------------------------------------------------------------
# Rutas entre anclas consecutivas
# ---------------------------------------------------------------------

coords_total = []

print("\nRutas entre puntos de control:\n")

for a, b in zip(anchors, anchors[1:]):
    path, length = dijkstra(graph, a["node"], b["node"])

    if path is None:
        raise SystemExit(
            f"ERROR: no existe ruta entre km {a['km']:.0f} y km {b['km']:.0f}."
        )

    factor = length / 1000 / (b["km"] - a["km"])

    print(
        f"km {a['km']:>5.0f} -> {b['km']:<5.0f} | "
        f"{length/1000:>7.2f} km | factor {factor:>5.3f} | "
        f"{len(path):>5} vertices"
    )

    if coords_total and path[0] == coords_total[-1]:
        path = path[1:]
    coords_total.extend(path)

# Limpiar duplicados consecutivos
clean = []
for p in coords_total:
    if not clean or p != clean[-1]:
        clean.append(p)

if len(clean) < 2:
    raise SystemExit("ERROR: traza final vacia.")

traza_xy = LineString(clean)
traza_ll = LineString([lonlat(x, y) for x, y in clean])

print("\nResultado:")
print(f"Vertices finales: {len(clean)}")
print(f"Longitud total: {traza_xy.length/1000:.2f} km")

# ---------------------------------------------------------------------
# Verificacion
# ---------------------------------------------------------------------

print("\nVerificacion contra puntos GPS:\n")
print(f"{'km':>6} {'s_traza':>10} {'dist':>9}")
print("-" * 29)

for r in pcs:
    p = Point(*xy(float(r["lon"]), float(r["lat"])))
    km = float(r["progresiva_km"])
    s = traza_xy.project(p) / 1000
    lateral = traza_xy.distance(p)
    print(f"{km:>6.0f} {s:>10.2f} {lateral:>7.1f} m")

salida = {
    "type": "Feature",
    "geometry": mapping(traza_ll),
    "properties": {
        "fuente": "openstreetmap+puntos_control",
        "metodo": "shortest_path_osm_snap_sobre_aristas",
        "tolerancia_gap_m": TOLERANCIA_GAP_M,
        "vertices": len(clean),
        "longitud_km": round(traza_xy.length / 1000, 3),
    },
}

SALIDA.write_text(json.dumps(salida, ensure_ascii=False), encoding="utf-8")
print(f"\nGuardado:\n{SALIDA}")
