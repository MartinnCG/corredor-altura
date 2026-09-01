from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask


ROOT = Path(__file__).resolve().parents[3]

SEGMENTOS = ROOT / "data" / "processed" / "segmentos.geojson"
DEM = ROOT / "data" / "processed" / "topografia" / "dem_corredor_500m_utm19s.tif"
PENDIENTE = ROOT / "data" / "processed" / "topografia" / "pendiente_terreno_pct.tif"

SALIDA = (
    ROOT
    / "data"
    / "processed"
    / "topografia"
    / "features_terreno_segmentos.csv"
)

CRS_METRICO = "EPSG:32719"
BUFFER_M = 250.0


def extraer_valores(src, geometria):
    datos, _ = mask(
        src,
        [geometria],
        crop=True,
        filled=False,
    )

    arr = datos[0]

    if np.ma.isMaskedArray(arr):
        valores = arr.compressed()
    else:
        valores = arr.ravel()

    valores = valores[np.isfinite(valores)]

    return valores


def main():
    segmentos = gpd.read_file(SEGMENTOS).to_crs(CRS_METRICO)

    filas = []

    with rasterio.open(DEM) as dem_src, rasterio.open(PENDIENTE) as slope_src:

        if dem_src.crs != slope_src.crs:
            raise ValueError("DEM y raster de pendiente tienen CRS diferentes.")

        for _, seg in segmentos.iterrows():
            zona = seg.geometry.buffer(BUFFER_M)

            elev = extraer_valores(dem_src, zona)
            slope = extraer_valores(slope_src, zona)

            if len(elev) == 0 or len(slope) == 0:
                raise ValueError(
                    f"Sin datos raster para segmento "
                    f"{seg['km_inicio']}-{seg['km_fin']}"
                )

            filas.append(
                {
                    "km_inicio": int(seg["km_inicio"]),
                    "km_fin": int(seg["km_fin"]),
                    "buffer_m": BUFFER_M,
                    "pendiente_terreno_media_pct": float(np.mean(slope)),
                    "pendiente_terreno_p90_pct": float(np.percentile(slope, 90)),
                    "relieve_local_m": float(np.max(elev) - np.min(elev)),
                    "n_celdas_pendiente": int(len(slope)),
                    "n_celdas_elevacion": int(len(elev)),
                }
            )

    df = pd.DataFrame(filas)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SALIDA, index=False)

    print("=== TERRENO POR SEGMENTO ===")
    print("Archivo:", SALIDA.relative_to(ROOT))
    print("Segmentos:", len(df))
    print("Valores faltantes:", int(df.isna().sum().sum()))

    print()
    print(
        df[
            [
                "pendiente_terreno_media_pct",
                "pendiente_terreno_p90_pct",
                "relieve_local_m",
            ]
        ].describe()
    )

    print()
    print("Top 10 por pendiente p90:")
    print(
        df.nlargest(10, "pendiente_terreno_p90_pct")[
            [
                "km_inicio",
                "km_fin",
                "pendiente_terreno_media_pct",
                "pendiente_terreno_p90_pct",
                "relieve_local_m",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
