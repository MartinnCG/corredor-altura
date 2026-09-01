from pathlib import Path

import numpy as np
import rasterio
from pysheds.grid import Grid


ROOT = Path(__file__).resolve().parents[3]

DEM = (
    ROOT
    / "data"
    / "processed"
    / "topografia"
    / "dem_hidrologia_acondicionado.tif"
)

FLOWDIR_OUT = (
    ROOT
    / "data"
    / "processed"
    / "topografia"
    / "flow_direction.tif"
)

ACC_OUT = (
    ROOT
    / "data"
    / "processed"
    / "topografia"
    / "flow_accumulation.tif"
)

# Convención D8 de pysheds:
# N, NE, E, SE, S, SW, W, NW
DMAP = (64, 128, 1, 2, 4, 8, 16, 32)


def guardar_raster(path, arr, perfil, dtype, nodata):
    out_profile = perfil.copy()
    out_profile.update(
        dtype=dtype,
        count=1,
        nodata=nodata,
        compress="deflate",
        tiled=True,
    )

    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(arr.astype(dtype), 1)


def main():
    grid = Grid.from_raster(str(DEM))
    dem = grid.read_raster(str(DEM))

    fdir = grid.flowdir(
        dem,
        dirmap=DMAP,
    )

    acc = grid.accumulation(
        fdir,
        dirmap=DMAP,
    )

    with rasterio.open(DEM) as src:
        perfil = src.profile.copy()
        dem_arr = src.read(1)
        dem_nodata = src.nodata

    mascara = np.isclose(dem_arr, dem_nodata)

    fdir_arr = np.asarray(fdir)
    acc_arr = np.asarray(acc, dtype="float64")

    fdir_nodata = 0
    acc_nodata = -9999.0

    fdir_arr[mascara] = fdir_nodata
    acc_arr[mascara] = acc_nodata

    guardar_raster(
        FLOWDIR_OUT,
        fdir_arr,
        perfil,
        "uint8",
        fdir_nodata,
    )

    guardar_raster(
        ACC_OUT,
        acc_arr,
        perfil,
        "float32",
        acc_nodata,
    )

    validos = acc_arr[
        np.isfinite(acc_arr)
        & (acc_arr != acc_nodata)
    ]

    print("=== FLUJO HIDROLOGICO ===")
    print("Flow direction:", FLOWDIR_OUT.relative_to(ROOT))
    print("Flow accumulation:", ACC_OUT.relative_to(ROOT))
    print("Celdas validas:", len(validos))
    print("Acumulacion min:", float(validos.min()))
    print("Acumulacion media:", float(validos.mean()))
    print("Acumulacion p90:", float(np.percentile(validos, 90)))
    print("Acumulacion p99:", float(np.percentile(validos, 99)))
    print("Acumulacion max:", float(validos.max()))


if __name__ == "__main__":
    main()
