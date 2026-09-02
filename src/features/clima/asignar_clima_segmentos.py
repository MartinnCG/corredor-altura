from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator


ROOT = Path(__file__).resolve().parents[3]

SEGMENTOS_FILE = ROOT / "data" / "processed" / "segmentos.geojson"
CLIMA_CELDAS_FILE = (
    ROOT
    / "data"
    / "processed"
    / "clima"
    / "features_clima_celdas_2001_2025.csv"
)

OUT_FILE = (
    ROOT
    / "data"
    / "processed"
    / "clima"
    / "features_clima_segmentos.csv"
)


FEATURES_CLIMA = [
    "temp_media_2001_2025_c",
    "dias_min_bajo_0c_anuales",
    "dias_congelamiento_deshielo_anuales",
    "precipitacion_anual_media_mm",
    "precipitacion_diaria_p95_mm",
    "viento_medio_ms",
    "viento_p95_ms",
    "fraccion_horas_nieve_gt0pct",
    "fraccion_horas_nieve_ge10pct",
    "fraccion_horas_nieve_ge50pct",
    "nieve_profundidad_p95_m",
    "cobertura_nieve_media_pct",
]


def construir_interpolador(df, feature):
    latitudes = np.sort(df["latitude"].unique())
    longitudes = np.sort(df["longitude"].unique())

    grilla = (
        df.pivot(
            index="latitude",
            columns="longitude",
            values=feature,
        )
        .reindex(
            index=latitudes,
            columns=longitudes,
        )
        .to_numpy()
    )

    if np.isnan(grilla).any():
        raise ValueError(
            f"La grilla de {feature} contiene valores faltantes."
        )

    return RegularGridInterpolator(
        (latitudes, longitudes),
        grilla,
        method="linear",
        bounds_error=True,
    )


def main():
    segmentos = gpd.read_file(SEGMENTOS_FILE)

    if segmentos.crs is None:
        raise ValueError("segmentos.geojson no tiene CRS.")

    if segmentos.crs.to_epsg() != 4326:
        segmentos = segmentos.to_crs(4326)

    clima = pd.read_csv(CLIMA_CELDAS_FILE)

    faltantes = [
        c
        for c in FEATURES_CLIMA
        if c not in clima.columns
    ]

    if faltantes:
        raise ValueError(
            "Faltan features climaticas: "
            + ", ".join(faltantes)
        )

    if len(segmentos) != 130:
        raise ValueError(
            f"Se esperaban 130 segmentos y hay {len(segmentos)}."
        )

    # Punto medio sobre la longitud real del segmento.
    # Se calcula en UTM 19S para evitar operar en grados.
    segmentos_utm = segmentos.to_crs(32719)

    centros_utm = segmentos_utm.geometry.interpolate(
        0.5,
        normalized=True,
    )

    centros = gpd.GeoSeries(
        centros_utm,
        crs=32719,
    ).to_crs(4326)

    salida = segmentos[
        [
            "km_inicio",
            "km_fin",
        ]
    ].copy()

    salida["latitud_centro"] = centros.y
    salida["longitud_centro"] = centros.x

    puntos = np.column_stack(
        [
            salida["latitud_centro"].to_numpy(),
            salida["longitud_centro"].to_numpy(),
        ]
    )

    for feature in FEATURES_CLIMA:
        interpolador = construir_interpolador(
            clima,
            feature,
        )

        salida[feature] = interpolador(puntos)

    if salida[FEATURES_CLIMA].isna().any().any():
        raise ValueError(
            "La interpolacion genero valores faltantes."
        )

    salida["metodo_clima"] = (
        "ERA5-Land ARCO 2001-2025; "
        "interpolacion bilineal en centro de segmento"
    )

    salida.to_csv(
        OUT_FILE,
        index=False,
    )

    print("=== CLIMA POR SEGMENTO ===")
    print("Filas:", len(salida))
    print("Features:", len(FEATURES_CLIMA))
    print("Faltantes:", int(
        salida[FEATURES_CLIMA]
        .isna()
        .sum()
        .sum()
    ))

    print("\nRango espacial centros:")
    print(
        "Lat:",
        salida["latitud_centro"].min(),
        "->",
        salida["latitud_centro"].max(),
    )
    print(
        "Lon:",
        salida["longitud_centro"].min(),
        "->",
        salida["longitud_centro"].max(),
    )

    print("\nResumen features:")
    print(
        salida[FEATURES_CLIMA]
        .describe()
        .T
    )

    print(
        "\nArchivo:",
        OUT_FILE.relative_to(ROOT),
    )


if __name__ == "__main__":
    main()
