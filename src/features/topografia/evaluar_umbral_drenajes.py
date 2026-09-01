from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask


ROOT = Path(__file__).resolve().parents[3]

SEGMENTOS = ROOT / "data" / "processed" / "segmentos.geojson"
ACC = ROOT / "data" / "processed" / "topografia" / "flow_accumulation.tif"

CRS_METRICO = "EPSG:32719"
BUFFER_M = 100.0

UMBRALES = [500, 1000, 2500, 5000, 10000]


def main():
    segmentos = gpd.read_file(SEGMENTOS).to_crs(CRS_METRICO)
    corredor = segmentos.geometry.union_all().buffer(BUFFER_M)

    with rasterio.open(ACC) as src:
        datos, _ = mask(
            src,
            [corredor],
            crop=True,
            filled=False,
        )

        arr = datos[0]

        if np.ma.isMaskedArray(arr):
            valores = arr.compressed()
        else:
            valores = arr.ravel()

        valores = valores[np.isfinite(valores)]
        valores = valores[valores >= 0]

        area_celda_km2 = abs(src.res[0] * src.res[1]) / 1_000_000

    print("=== DIAGNOSTICO UMBRALES DE DRENAJE ===")
    print("Buffer corredor:", BUFFER_M, "m")
    print("Celdas validas analizadas:", len(valores))
    print("Area por celda:", round(area_celda_km2, 6), "km2")
    print()

    for umbral in UMBRALES:
        n = int(np.sum(valores >= umbral))
        area_aportante = umbral * area_celda_km2

        print(
            f"Umbral {umbral:>5} celdas "
            f"(~{area_aportante:>6.2f} km2): "
            f"{n:>6} celdas cerca del corredor"
        )


if __name__ == "__main__":
    main()
