from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from shapely.geometry import LineString


ROOT = Path(__file__).resolve().parents[3]

SEGMENTOS = ROOT / "data" / "processed" / "segmentos.geojson"
DEM = ROOT / "data" / "processed" / "topografia" / "dem_corredor_500m.tif"
SALIDA = ROOT / "data" / "processed" / "topografia" / "features_pendiente_longitudinal.csv"

CRS_METRICO = "EPSG:32719"
PASO_M = 30.0


def sample_line(line_m: LineString, step_m: float):
    length = line_m.length
    distances = np.arange(0, length, step_m)

    if len(distances) == 0 or distances[-1] < length:
        distances = np.append(distances, length)

    points = [line_m.interpolate(d) for d in distances]
    return distances, points


def main():
    gdf = gpd.read_file(SEGMENTOS)
    gdf_m = gdf.to_crs(CRS_METRICO)

    resultados = []

    print("=== PENDIENTE LONGITUDINAL POR SEGMENTO ===")
    print("Segmentos:", len(gdf))
    print("Paso de muestreo:", PASO_M, "m")

    with rasterio.open(DEM) as src:
        for idx, row_m in gdf_m.iterrows():
            line_m = row_m.geometry
            distances, points_m = sample_line(line_m, PASO_M)

            points_gdf = gpd.GeoDataFrame(
                geometry=points_m,
                crs=CRS_METRICO,
            ).to_crs(src.crs)

            coords = [(p.x, p.y) for p in points_gdf.geometry]
            elevaciones = np.array(
                [float(v[0]) for v in src.sample(coords)],
                dtype=float
            )

            if src.nodata is not None:
                elevaciones[np.isclose(elevaciones, src.nodata)] = np.nan

            valid = ~np.isnan(elevaciones)

            if valid.sum() < 2:
                resultados.append({
                    "km_inicio": row_m["km_inicio"],
                    "km_fin": row_m["km_fin"],
                    "elev_inicio_m": np.nan,
                    "elev_fin_m": np.nan,
                    "desnivel_neto_m": np.nan,
                    "pendiente_neta_pct": np.nan,
                    "pendiente_media_abs_pct": np.nan,
                    "pendiente_max_abs_pct": np.nan,
                    "n_muestras": int(valid.sum()),
                })
                continue

            elev = elevaciones[valid]
            dist = distances[valid]

            delta_z = np.diff(elev)
            delta_d = np.diff(dist)

            # Evita pendientes artificiales causadas por el
            # intervalo residual corto al final del segmento.
            intervalos_validos = delta_d >= 20.0

            pendientes_pct = (
                delta_z[intervalos_validos]
                / delta_d[intervalos_validos]
            ) * 100.0

            desnivel_neto = elev[-1] - elev[0]
            distancia_total = dist[-1] - dist[0]
            pendiente_neta = (desnivel_neto / distancia_total) * 100.0

            resultados.append({
                "km_inicio": row_m["km_inicio"],
                "km_fin": row_m["km_fin"],
                "elev_inicio_m": float(elev[0]),
                "elev_fin_m": float(elev[-1]),
                "desnivel_neto_m": float(desnivel_neto),
                "pendiente_neta_pct": float(pendiente_neta),
                "pendiente_media_abs_pct": float(np.mean(np.abs(pendientes_pct))),
                "pendiente_max_abs_pct": float(np.max(np.abs(pendientes_pct))),
                "n_muestras": int(len(elev)),
            })

    df = pd.DataFrame(resultados)
    df.to_csv(SALIDA, index=False)

    print("\nResultado:")
    print("Archivo:", SALIDA.relative_to(ROOT))
    print("Filas:", len(df))
    print("Segmentos sin pendiente:", df["pendiente_neta_pct"].isna().sum())

    print("\nResumen:")
    print(df[
        [
            "desnivel_neto_m",
            "pendiente_neta_pct",
            "pendiente_media_abs_pct",
            "pendiente_max_abs_pct",
        ]
    ].describe())


if __name__ == "__main__":
    main()
