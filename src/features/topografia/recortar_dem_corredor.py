from pathlib import Path

import geopandas as gpd
import rasterio
from rasterio.mask import mask


ROOT = Path(__file__).resolve().parents[3]

SEGMENTOS = ROOT / "data" / "processed" / "segmentos.geojson"
DEM = ROOT / "data" / "processed" / "topografia" / "dem_mdear_30m_mosaico.tif"
SALIDA = ROOT / "data" / "processed" / "topografia" / "dem_corredor_500m.tif"

CRS_METRICO = "EPSG:32719"
BUFFER_M = 500


def main():
    segmentos = gpd.read_file(SEGMENTOS)

    print("=== RECORTE DEM CORREDOR 0-130 ===")
    print("Segmentos:", len(segmentos))
    print("CRS original:", segmentos.crs)

    # Reproyección a CRS métrico para construir un buffer real de 500 m
    segmentos_m = segmentos.to_crs(CRS_METRICO)

    geometria_corredor = segmentos_m.geometry.union_all()
    buffer_m = geometria_corredor.buffer(BUFFER_M)

    buffer_gdf = gpd.GeoDataFrame(
        geometry=[buffer_m],
        crs=CRS_METRICO,
    )

    with rasterio.open(DEM) as src:
        buffer_dem_crs = buffer_gdf.to_crs(src.crs)

        imagen, transform = mask(
            src,
            buffer_dem_crs.geometry,
            crop=True,
            nodata=src.nodata,
        )

        perfil = src.profile.copy()
        perfil.update(
            height=imagen.shape[1],
            width=imagen.shape[2],
            transform=transform,
            compress="deflate",
            tiled=True,
        )

        with rasterio.open(SALIDA, "w", **perfil) as dst:
            dst.write(imagen)

    with rasterio.open(SALIDA) as src:
        arr = src.read(1, masked=True)

        print("\nResultado:")
        print("Archivo:", SALIDA.relative_to(ROOT))
        print("CRS:", src.crs)
        print("Resolución:", src.res)
        print("Tamaño:", src.width, "x", src.height)
        print("Bounds:", src.bounds)
        print("Elevación min:", float(arr.min()))
        print("Elevación max:", float(arr.max()))


if __name__ == "__main__":
    main()
