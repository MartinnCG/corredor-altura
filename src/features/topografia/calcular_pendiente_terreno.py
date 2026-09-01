from pathlib import Path

import numpy as np
import rasterio


ROOT = Path(__file__).resolve().parents[3]

DEM = ROOT / "data" / "processed" / "topografia" / "dem_corredor_500m_utm19s.tif"
SALIDA = ROOT / "data" / "processed" / "topografia" / "pendiente_terreno_pct.tif"


def main():
    with rasterio.open(DEM) as src:
        elev = src.read(1).astype("float64")
        nodata = src.nodata

        mask = np.isclose(elev, nodata)
        elev[mask] = np.nan

        res_x, res_y = src.res

        dz_dy, dz_dx = np.gradient(
            elev,
            res_y,
            res_x,
        )

        pendiente_pct = np.sqrt(dz_dx**2 + dz_dy**2) * 100.0

        # np.gradient propaga NaN hacia celdas vecinas del borde NoData.
        # Todo resultado no finito se devuelve explícitamente a NoData.
        pendiente_pct[~np.isfinite(pendiente_pct)] = nodata

        perfil = src.profile.copy()
        perfil.update(
            dtype="float32",
            count=1,
            nodata=nodata,
            compress="deflate",
            tiled=True,
        )

        with rasterio.open(SALIDA, "w", **perfil) as dst:
            dst.write(pendiente_pct.astype("float32"), 1)

    with rasterio.open(SALIDA) as src:
        arr = src.read(1, masked=True)

        print("=== PENDIENTE DEL TERRENO ===")
        print("Archivo:", SALIDA.relative_to(ROOT))
        print("CRS:", src.crs)
        print("Resolución:", src.res)
        print("Pendiente min:", float(arr.min()))
        print("Pendiente media:", float(arr.mean()))
        print("Pendiente max:", float(arr.max()))


if __name__ == "__main__":
    main()
