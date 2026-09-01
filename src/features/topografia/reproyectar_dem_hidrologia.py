from pathlib import Path

import rasterio
from rasterio.warp import (
    calculate_default_transform,
    reproject,
    Resampling,
)


ROOT = Path(__file__).resolve().parents[3]

ENTRADA = (
    ROOT
    / "data"
    / "processed"
    / "topografia"
    / "dem_mdear_30m_mosaico.tif"
)

SALIDA = (
    ROOT
    / "data"
    / "processed"
    / "topografia"
    / "dem_mdear_30m_utm19s.tif"
)

DST_CRS = "EPSG:32719"


def main():
    with rasterio.open(ENTRADA) as src:
        transform, width, height = calculate_default_transform(
            src.crs,
            DST_CRS,
            src.width,
            src.height,
            *src.bounds,
        )

        perfil = src.profile.copy()
        perfil.update(
            crs=DST_CRS,
            transform=transform,
            width=width,
            height=height,
            compress="deflate",
            tiled=True,
        )

        with rasterio.open(SALIDA, "w", **perfil) as dst:
            for banda in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, banda),
                    destination=rasterio.band(dst, banda),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=DST_CRS,
                    src_nodata=src.nodata,
                    dst_nodata=src.nodata,
                    resampling=Resampling.bilinear,
                )

    with rasterio.open(SALIDA) as src:
        print("=== DEM HIDROLOGIA UTM ===")
        print("Archivo:", SALIDA.relative_to(ROOT))
        print("CRS:", src.crs)
        print("Resolución:", src.res)
        print("Tamaño:", src.width, "x", src.height)
        print("Bounds:", src.bounds)
        print("NoData:", src.nodata)


if __name__ == "__main__":
    main()
