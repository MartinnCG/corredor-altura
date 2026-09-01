from pathlib import Path

import numpy as np
import pandas as pd
import rasterio


ROOT = Path(__file__).resolve().parents[3]

REFERENCIAS = ROOT / "data" / "raw" / "elevaciones_referencia.csv"
DEM = ROOT / "data" / "processed" / "topografia" / "dem_corredor_500m.tif"
SALIDA = ROOT / "data" / "processed" / "topografia" / "validacion_dem_referencias.csv"


def main():
    df = pd.read_csv(REFERENCIAS)

    with rasterio.open(DEM) as src:
        coords = list(zip(df["lon"], df["lat"]))
        muestras = list(src.sample(coords))

        df["elev_dem_m"] = [float(x[0]) for x in muestras]

        if src.nodata is not None:
            df.loc[
                np.isclose(df["elev_dem_m"], src.nodata),
                "elev_dem_m"
            ] = np.nan

    df["error_m"] = df["elev_dem_m"] - df["elevacion_m"]
    df["error_abs_m"] = df["error_m"].abs()

    valid = df.dropna(subset=["elevacion_m", "elev_dem_m"])

    mae = valid["error_abs_m"].mean()
    rmse = np.sqrt((valid["error_m"] ** 2).mean())
    sesgo = valid["error_m"].mean()

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SALIDA, index=False)

    print("=== VALIDACION MDE-Ar vs REFERENCIAS GOOGLE EARTH ===")
    print("Puntos totales:", len(df))
    print("Puntos comparables:", len(valid))
    print(f"MAE:   {mae:.2f} m")
    print(f"RMSE:  {rmse:.2f} m")
    print(f"Sesgo: {sesgo:+.2f} m")
    print("Error máximo absoluto:", f"{valid['error_abs_m'].max():.2f} m")
    print("Archivo:", SALIDA.relative_to(ROOT))


if __name__ == "__main__":
    main()
