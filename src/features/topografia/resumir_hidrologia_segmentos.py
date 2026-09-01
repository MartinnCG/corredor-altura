from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask


ROOT = Path(__file__).resolve().parents[3]

SEGMENTOS = ROOT / "data" / "processed" / "segmentos.geojson"
SEC = ROOT / "data" / "processed" / "topografia" / "drenajes_secundarios.geojson"
PRI = ROOT / "data" / "processed" / "topografia" / "drenajes_principales.geojson"
ACC = ROOT / "data" / "processed" / "topografia" / "flow_accumulation.tif"

SALIDA = (
    ROOT
    / "data"
    / "processed"
    / "topografia"
    / "features_hidrologia_segmentos.csv"
)

BUFFER_M = 50.0


def main():
    with rasterio.open(ACC) as src:
        crs = src.crs
        nodata = src.nodata

        area_celda_km2 = (
            abs(src.res[0] * src.res[1]) / 1_000_000
        )

        segmentos = gpd.read_file(SEGMENTOS).to_crs(crs)
        secundarios = gpd.read_file(SEC).to_crs(crs)
        principales = gpd.read_file(PRI).to_crs(crs)

        filas = []

        for _, seg in segmentos.iterrows():
            entorno = seg.geometry.buffer(BUFFER_M)

            sec_cerca = secundarios[
                secundarios.intersects(entorno)
            ]

            pri_cerca = principales[
                principales.intersects(entorno)
            ]

            arr, _ = mask(
                src,
                [entorno],
                crop=True,
                filled=False,
            )

            vals = arr[0].compressed().astype(float)

            vals = vals[
                np.isfinite(vals)
                & (vals >= 1)
            ]

            if nodata is not None:
                vals = vals[vals != nodata]

            if len(vals):
                acc_max = float(np.max(vals))
                area_max = acc_max * area_celda_km2
            else:
                acc_max = np.nan
                area_max = np.nan

            filas.append(
                {
                    "km_inicio": int(seg["km_inicio"]),
                    "km_fin": int(seg["km_fin"]),
                    "buffer_hidrologia_m": BUFFER_M,

                    "drenaje_secundario_50m":
                        int(len(sec_cerca) > 0),

                    "drenaje_principal_50m":
                        int(len(pri_cerca) > 0),

                    "n_drenajes_secundarios_50m":
                        int(len(sec_cerca)),

                    "n_drenajes_principales_50m":
                        int(len(pri_cerca)),

                    "acumulacion_max_50m_celdas":
                        acc_max,

                    "area_aportante_max_50m_km2":
                        area_max,
                }
            )

    df = pd.DataFrame(filas)
    df.to_csv(SALIDA, index=False)

    print("=== FEATURES HIDROLOGIA ===")
    print("Segmentos:", len(df))
    print("Missing area:", df["area_aportante_max_50m_km2"].isna().sum())

    print("\nSegmentos con drenaje secundario <=50 m:",
          int(df["drenaje_secundario_50m"].sum()))

    print("Segmentos con drenaje principal <=50 m:",
          int(df["drenaje_principal_50m"].sum()))

    print("\nArea aportante maxima (km2):")
    print(df["area_aportante_max_50m_km2"].describe())

    print("\nTOP 15:")
    print(
        df[
            [
                "km_inicio",
                "km_fin",
                "drenaje_principal_50m",
                "n_drenajes_principales_50m",
                "area_aportante_max_50m_km2",
            ]
        ]
        .sort_values(
            "area_aportante_max_50m_km2",
            ascending=False,
        )
        .head(15)
        .to_string(index=False)
    )

    print("\nArchivo:", SALIDA.relative_to(ROOT))


if __name__ == "__main__":
    main()
