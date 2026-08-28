"""Proyecta las elevaciones de referencia sobre los segmentos del corredor
y construye el perfil altimetrico.

Las elevaciones son mediciones puntuales sin progresiva asignada. Se les
asigna la del segmento mas cercano, y se descarta toda medicion que caiga
a mas de TOL_M del eje del corredor.
"""

import csv, json, math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parents[2]
SEG = list(csv.DictReader(open(RAIZ / "data" / "processed" / "segmentos.csv", encoding="utf-8")))
ELE = list(csv.DictReader(open(RAIZ / "data" / "raw" / "elevaciones_referencia.csv", encoding="utf-8")))
OUT_CSV = RAIZ / "data" / "processed" / "perfil_altimetrico.csv"
OUT_PNG = RAIZ / "outputs" / "perfil_altimetrico.png"

TOL_M = 1500

LAT_REF = -29.1
MX = 111320 * math.cos(math.radians(LAT_REF))
MY = 110540


def xy(lon, lat):
    return lon * MX, lat * MY


centros = [(float(s["km_inicio"]) + 0.5, *xy(float(s["lon_centro"]), float(s["lat_centro"])))
           for s in SEG]

filas, descartadas = [], 0
for e in ELE:
    if not e["elevacion_m"]:
        continue
    ex, ey = xy(float(e["lon"]), float(e["lat"]))
    km, d = min(((c[0], math.hypot(ex - c[1], ey - c[2])) for c in centros),
                key=lambda t: t[1])
    if d > TOL_M:
        descartadas += 1
        continue
    filas.append({
        "progresiva_km": f"{km:.1f}",
        "elevacion_m": e["elevacion_m"],
        "toponimo": e["toponimo"],
        "desvio_eje_m": f"{d:.0f}",
        "fuente": e["fuente"],
    })

filas.sort(key=lambda r: float(r["progresiva_km"]))

with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
    w.writeheader()
    w.writerows(filas)

print(f"Elevaciones asignadas: {len(filas)}   descartadas: {descartadas}\n")
print(f"{'km':>7} {'msnm':>9} {'desvio':>8}  toponimo")
print("-" * 50)
for r in filas:
    print(f"{float(r['progresiva_km']):>7.1f} {float(r['elevacion_m']):>9.0f} "
          f"{r['desvio_eje_m']:>7} m  {r['toponimo']}")
print("-" * 50)

kms = [float(r["progresiva_km"]) for r in filas]
els = [float(r["elevacion_m"]) for r in filas]

print(f"\nRango: {min(els):.0f} a {max(els):.0f} m   desnivel {max(els)-min(els):.0f} m")

# pendiente media entre mediciones consecutivas
print(f"\nPendiente media por tramo:\n")
print(f"{'tramo km':>14} {'desnivel':>10} {'pendiente':>11}")
print("-" * 38)
for (k0, e0), (k1, e1) in zip(zip(kms, els), zip(kms[1:], els[1:])):
    if k1 > k0:
        p = (e1 - e0) / ((k1 - k0) * 1000) * 100
        print(f"{k0:>6.0f} a {k1:>5.0f} {e1-e0:>+9.0f} m {p:>+10.2f} %")

fig, ax = plt.subplots(figsize=(13, 5))
ax.plot(kms, els, "-", color="#8b6f47", lw=1.4, zorder=2)
ax.fill_between(kms, min(els) - 100, els, color="#d4c4a8", alpha=0.55, zorder=1)
ax.scatter(kms, els, s=22, color="#5c4a32", zorder=3)

for r in filas:
    if r["toponimo"]:
        ax.annotate(r["toponimo"],
                    (float(r["progresiva_km"]), float(r["elevacion_m"])),
                    textcoords="offset points", xytext=(0, 11),
                    ha="center", fontsize=7.5, rotation=32, color="#3d3226")

ax.set_xlabel("Progresiva (km desde Garita Portal Guandacol)")
ax.set_ylabel("Elevación (m s.n.m.)")
ax.set_title("Perfil altimétrico — Corredor de acceso este, Proyecto Vicuña", pad=14)
ax.grid(alpha=0.25, ls="--", lw=0.6)
ax.set_ylim(min(els) - 100, max(els) + 350)
ax.set_xlim(-2, max(kms) + 3)
fig.tight_layout()

OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PNG, dpi=170)
print(f"\nGuardado:\n  {OUT_CSV}\n  {OUT_PNG}")
