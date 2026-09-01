from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping


ROOT = Path(__file__).resolve().parents[3]

SEGMENTOS = ROOT / "data" / "processed" / "segmentos.geojson"
DEM = ROOT / "data" / "processed" / "topografia" / "dem_corredor_500m.tif"
SALIDA = ROOT / "data" / "processed" / "topografia" / "features_elevacion_segmentos.csv"

CRS_METRICO = "EPSG:32719"
BUFFER_M = 30


def main():
    segmentos = gpd.read_file(SEGMENTOS)

    print("=== EXTRACCION DE ELEVACION POR SEGMENTO ===")
    print("Segmentos:", len(segmentos))

    # Buffer estrecho alrededor de cada segmento para capturar celdas DEM
    segmentos_m = segmentos.to_crs(CRS_METRICO)

    resultados = []

    with rasterio.open(DEM) as src:
        for idx, row in segmentos_m.iterrows():
            geom_buffer = row.geometry.buffer(BUFFER_M)

            geom_gdf = gpd.GeoDataFrame(
                geometry=[geom_buffer],
                crs=CRS_METRICO,
            ).to_crs(src.crs)

            imagen, _ = mask(
                src,
                [mapping(geom_gdf.geometry.iloc[0])],
                crop=True,
                filled=False,
            )

            datos = imagen[0]
            validos = datos.compressed()

            if len(validos) == 0:
                elev_min = None
                elev_mean = None
                elev_max = None
            else:
                elev_min = float(validos.min())
                elev_mean = float(validos.mean())
                elev_max = float(validos.max())

            resultados.append({
                "km_inicio": row["km_inicio"],
                "km_fin": row["km_fin"],
                "elev_min_m": elev_min,
                "elev_mean_m": elev_mean,
                "elev_max_m": elev_max,
                "desnivel_local_m": (
                    elev_max - elev_min
                    if elev_min is not None and elev_max is not None
                    else None
                ),
            })

    df = pd.DataFrame(resultados)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SALIDA, index=False)

    print("\nResultado:")
    print("Archivo:", SALIDA.relative_to(ROOT))
    print("Filas:", len(df))
    print("Segmentos sin datos:", df["elev_mean_m"].isna().sum())

    print("\nResumen:")
    print(df[
        ["elev_min_m", "elev_mean_m", "elev_max_m", "desnivel_local_m"]
    ].describe())


if __name__ == "__main__":
    main()
