from pathlib import Path

import numpy as np
import rasterio
from pysheds.grid import Grid


ROOT = Path(__file__).resolve().parents[3]

ENTRADA = (
    ROOT
    / "data"
    / "processed"
    / "topografia"
    / "dem_mdear_30m_utm19s.tif"
)

SALIDA = (
    ROOT
    / "data"
    / "processed"
    / "topografia"
    / "dem_hidrologia_acondicionado.tif"
)


def main():
    grid = Grid.from_raster(str(ENTRADA))
    dem = grid.read_raster(str(ENTRADA))

    dem_filled = grid.fill_depressions(dem)
    dem_filled = grid.resolve_flats(dem_filled)

    with rasterio.open(ENTRADA) as src:
        perfil = src.profile.copy()
        nodata = src.nodata

        arr = np.asarray(dem_filled, dtype="float32")

        perfil.update(
            dtype="float32",
            count=1,
            compress="deflate",
            tiled=True,
        )

        with rasterio.open(SALIDA, "w", **perfil) as dst:
            dst.write(arr, 1)

    validos = arr[np.isfinite(arr) & (arr != nodata)]

    print("=== DEM HIDROLOGICAMENTE ACONDICIONADO ===")
    print("Archivo:", SALIDA.relative_to(ROOT))
    print("Celdas validas:", len(validos))
    print("Elevacion min:", float(validos.min()))
    print("Elevacion media:", float(validos.mean()))
    print("Elevacion max:", float(validos.max()))


if __name__ == "__main__":
    main()
