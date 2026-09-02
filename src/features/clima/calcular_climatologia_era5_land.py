from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[3]

OUT_DIR = ROOT / "data" / "processed" / "clima"
OUT_FILE = OUT_DIR / "features_clima_celdas_2001_2025.csv"

INICIO = "2001-01-01T00:00:00"
FIN = "2025-12-31T23:00:00"

LAT_MIN = -29.6
LAT_MAX = -28.6
LON_MIN = -69.1
LON_MAX = -68.5

BASE = "https://arco.datastores.ecmwf.int/"

URL_TEMPERATURA = (
    BASE
    + "cadl-arco-geo-007/arco/reanalysis_era5_land/"
    + "sfc-2m-temperature/geoChunked.zarr"
)

URL_VIENTO = (
    BASE
    + "cadl-arco-geo-008/arco/reanalysis_era5_land/"
    + "sfc-wind/geoChunked.zarr"
)

URL_PRECIPITACION = (
    BASE
    + "cadl-arco-geo-009/arco/reanalysis_era5_land/"
    + "sfc-pressure-precipitation/geoChunked.zarr"
)

URL_NIEVE = (
    BASE
    + "cadl-arco-geo-030/arco/reanalysis_era5_land/"
    + "sfc-snow/geoChunked.zarr"
)


def leer_key():
    cfg = Path.home() / ".cdsapirc"

    for line in cfg.read_text().splitlines():
        if line.strip().startswith("key:"):
            key = line.split(":", 1)[1].strip()
            if key:
                return key

    raise RuntimeError(
        "No se encontro CDS API key en ~/.cdsapirc"
    )


def abrir_arco(url, key):
    return xr.open_zarr(
        url,
        consolidated=True,
        chunks=None,
        storage_options={
            "headers": {
                "Authorization": f"Bearer {key}"
            }
        },
    )


def subset(da):
    """
    Recorte temporal y espacial con tolerancia para evitar
    excluir celdas de borde por representación float.
    """
    eps = 1e-6

    da = da.sel(
        time=slice(INICIO, FIN),
    )

    return da.where(
        (da.latitude >= LAT_MIN - eps)
        & (da.latitude <= LAT_MAX + eps)
        & (da.longitude >= LON_MIN - eps)
        & (da.longitude <= LON_MAX + eps),
        drop=True,
    )


def a_dataframe(feature):
    df = feature.to_dataframe().reset_index()

    # Los percentiles de xarray agregan una coordenada
    # escalar "quantile"; no constituye una feature.
    return df.drop(
        columns=["quantile"],
        errors="ignore",
    )


def calcular_temperatura(key):
    print("\n[1/4] Temperatura")

    ds = abrir_arco(URL_TEMPERATURA, key)
    t = subset(ds["t2m"]).load() - 273.15

    print("shape:", tuple(t.shape))

    temp_media = (
        t.mean("time")
        .rename("temp_media_2001_2025_c")
    )

    diaria_min = t.resample(time="1D").min()
    diaria_max = t.resample(time="1D").max()

    dias_frio = (
        (diaria_min < 0)
        .groupby("time.year")
        .sum("time")
        .mean("year")
        .rename("dias_min_bajo_0c_anuales")
    )

    dias_freeze_thaw = (
        ((diaria_min <= 0) & (diaria_max > 0))
        .groupby("time.year")
        .sum("time")
        .mean("year")
        .rename("dias_congelamiento_deshielo_anuales")
    )

    df = a_dataframe(temp_media)

    df = df.merge(
        a_dataframe(dias_frio),
        on=["latitude", "longitude"],
    )

    df = df.merge(
        a_dataframe(dias_freeze_thaw),
        on=["latitude", "longitude"],
    )

    ds.close()
    return df


def calcular_precipitacion(key):
    print("\n[2/4] Precipitacion")

    ds = abrir_arco(URL_PRECIPITACION, key)

    tp = subset(ds["tp"]).load() * 1000.0

    print("shape:", tuple(tp.shape))

    diaria = tp.resample(time="1D").sum()

    anual = (
        diaria
        .groupby("time.year")
        .sum("time")
    )

    precip_anual_media = (
        anual
        .mean("year")
        .rename("precipitacion_anual_media_mm")
    )

    precip_diaria_p95 = (
        diaria
        .quantile(0.95, dim="time")
        .rename("precipitacion_diaria_p95_mm")
    )

    df = a_dataframe(precip_anual_media)

    df = df.merge(
        a_dataframe(precip_diaria_p95),
        on=["latitude", "longitude"],
    )

    ds.close()
    return df


def calcular_viento(key):
    print("\n[3/4] Viento")

    ds = abrir_arco(URL_VIENTO, key)

    u = subset(ds["u10"]).load()
    v = subset(ds["v10"]).load()

    viento = np.sqrt(u ** 2 + v ** 2)

    print("shape:", tuple(viento.shape))

    viento_medio = (
        viento
        .mean("time")
        .rename("viento_medio_ms")
    )

    viento_p95 = (
        viento
        .quantile(0.95, dim="time")
        .rename("viento_p95_ms")
    )

    df = a_dataframe(viento_medio)

    df = df.merge(
        a_dataframe(viento_p95),
        on=["latitude", "longitude"],
    )

    ds.close()
    return df


def calcular_nieve(key):
    print("\n[4/4] Nieve")

    ds = abrir_arco(URL_NIEVE, key)

    sde = subset(ds["sde"]).load()
    snowc = subset(ds["snowc"]).load()

    print("shape:", tuple(sde.shape))

    persistencia = (
        (snowc > 0)
        .mean("time")
        .rename("fraccion_horas_nieve_gt0pct")
    )

    persistencia_10 = (
        (snowc >= 10)
        .mean("time")
        .rename("fraccion_horas_nieve_ge10pct")
    )

    persistencia_50 = (
        (snowc >= 50)
        .mean("time")
        .rename("fraccion_horas_nieve_ge50pct")
    )

    nieve_p95 = (
        sde
        .quantile(0.95, dim="time")
        .rename("nieve_profundidad_p95_m")
    )

    cobertura_media = (
        snowc
        .mean("time")
        .rename("cobertura_nieve_media_pct")
    )

    df = a_dataframe(persistencia)

    df = df.merge(
        a_dataframe(persistencia_10),
        on=["latitude", "longitude"],
    )

    df = df.merge(
        a_dataframe(persistencia_50),
        on=["latitude", "longitude"],
    )

    df = df.merge(
        a_dataframe(nieve_p95),
        on=["latitude", "longitude"],
    )

    df = df.merge(
        a_dataframe(cobertura_media),
        on=["latitude", "longitude"],
    )

    ds.close()
    return df


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    key = leer_key()

    print("=== CLIMATOLOGIA ERA5-LAND ARCO ===")
    print("Periodo:", INICIO, "->", FIN)

    temp = calcular_temperatura(key)
    precip = calcular_precipitacion(key)
    viento = calcular_viento(key)
    nieve = calcular_nieve(key)

    claves = ["latitude", "longitude"]

    df = temp.merge(
        precip,
        on=claves,
        validate="one_to_one",
    )

    df = df.merge(
        viento,
        on=claves,
        validate="one_to_one",
    )

    df = df.merge(
        nieve,
        on=claves,
        validate="one_to_one",
    )

    df = df.sort_values(
        ["latitude", "longitude"],
        ascending=[False, True],
    ).reset_index(drop=True)

    if df.isna().any().any():
        faltantes = df.isna().sum()
        faltantes = faltantes[faltantes > 0]

        raise ValueError(
            "Hay valores faltantes:\n"
            + faltantes.to_string()
        )

    df.to_csv(
        OUT_FILE,
        index=False,
    )

    print("\n=== RESULTADO ===")
    print("Celdas:", len(df))
    print("Features:", len(df.columns) - 2)

    print("\nResumen:")
    print(
        df.drop(columns=claves)
        .describe()
        .T
    )

    print(
        "\nArchivo:",
        OUT_FILE.relative_to(ROOT),
    )


if __name__ == "__main__":
    main()
