from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT
    / "data"
    / "processed"
    / "features_segmentos_master.csv"
)

OUTPUT_FILE = (
    ROOT
    / "data"
    / "processed"
    / "indice_exposicion_segmentos.csv"
)


GRUPOS = {
    "topografia": [
        "pendiente_media_abs_pct",
        "pendiente_terreno_p90_pct",
    ],
    "hidrologia": [
        "n_drenajes_principales_50m",
        "area_aportante_max_50m_km2",
    ],
    "clima": [
        "precipitacion_diaria_p95_mm",
        "viento_p95_ms",
        "fraccion_horas_nieve_ge50pct",
    ],
}


def normalizar_robusto(serie):
    """
    Winsorizacion P5-P95 seguida de Min-Max 0-1.

    Reduce la influencia de valores extremos sin eliminar
    segmentos del analisis.
    """
    s = serie.astype(float)

    p05 = s.quantile(0.05)
    p95 = s.quantile(0.95)

    if np.isclose(p05, p95):
        raise ValueError(
            f"Variable sin variacion robusta: {serie.name}"
        )

    limitada = s.clip(
        lower=p05,
        upper=p95,
    )

    normalizada = (
        (limitada - p05)
        / (p95 - p05)
    )

    return normalizada, p05, p95


def main():
    df = pd.read_csv(INPUT_FILE)

    if len(df) != 130:
        raise ValueError(
            f"Se esperaban 130 segmentos y hay {len(df)}."
        )

    requeridas = [
        variable
        for variables in GRUPOS.values()
        for variable in variables
    ]

    faltantes = [
        c for c in requeridas
        if c not in df.columns
    ]

    if faltantes:
        raise ValueError(
            f"Faltan variables: {faltantes}"
        )

    salida = df[
        [
            "km_inicio",
            "km_fin",
        ]
    ].copy()

    print("=== ETAPA 3 — INDICE DE EXPOSICION ===")
    print("Segmentos:", len(df))

    print("\nVariables seleccionadas:")
    for grupo, variables in GRUPOS.items():
        print(f"\n{grupo.upper()}")
        for variable in variables:
            print("-", variable)

    parametros = []

    # ----------------------------
    # TOPografia
    # ----------------------------

    for variable in GRUPOS["topografia"]:
        nombre_norm = f"{variable}_norm"

        normalizada, p05, p95 = normalizar_robusto(
            df[variable]
        )

        salida[nombre_norm] = normalizada

        parametros.append(
            (variable, p05, p95)
        )

    # ----------------------------
    # HIDROLOGIA
    # ----------------------------

    drenajes = "n_drenajes_principales_50m"

    normalizada, p05, p95 = normalizar_robusto(
        df[drenajes]
    )

    salida[f"{drenajes}_norm"] = normalizada

    parametros.append(
        (drenajes, p05, p95)
    )

    area_original = (
        df["area_aportante_max_50m_km2"]
        .astype(float)
    )

    area_log = np.log1p(area_original)
    area_log.name = "log1p_area_aportante_max_50m_km2"

    normalizada, p05, p95 = normalizar_robusto(
        area_log
    )

    salida[
        "area_aportante_max_50m_km2_norm"
    ] = normalizada

    parametros.append(
        (
            "log1p_area_aportante_max_50m_km2",
            p05,
            p95,
        )
    )

    # ----------------------------
    # CLIMA
    # ----------------------------

    for variable in GRUPOS["clima"]:
        nombre_norm = f"{variable}_norm"

        normalizada, p05, p95 = normalizar_robusto(
            df[variable]
        )

        salida[nombre_norm] = normalizada

        parametros.append(
            (variable, p05, p95)
        )

    # ----------------------------
    # SUBINDICES
    # ----------------------------

    cols_topografia = [
        f"{v}_norm"
        for v in GRUPOS["topografia"]
    ]

    cols_hidrologia = [
        "n_drenajes_principales_50m_norm",
        "area_aportante_max_50m_km2_norm",
    ]

    cols_clima = [
        f"{v}_norm"
        for v in GRUPOS["clima"]
    ]

    salida["subindice_topografia"] = (
        salida[cols_topografia].mean(axis=1)
    )

    salida["subindice_hidrologia"] = (
        salida[cols_hidrologia].mean(axis=1)
    )

    salida["subindice_clima"] = (
        salida[cols_clima].mean(axis=1)
    )

    # Cada dimension pesa exactamente 1/3.
    salida["indice_exposicion"] = (
        salida[
            [
                "subindice_topografia",
                "subindice_hidrologia",
                "subindice_clima",
            ]
        ]
        .mean(axis=1)
        * 100.0
    )

    # Ranking: 1 = mayor exposicion.
    salida["ranking_exposicion"] = (
        salida["indice_exposicion"]
        .rank(
            method="min",
            ascending=False,
        )
        .astype(int)
    )

    # Clasificacion relativa por quintiles.
    salida["clase_exposicion"] = pd.qcut(
        salida["indice_exposicion"],
        q=5,
        labels=[
            "muy_baja",
            "baja",
            "media",
            "alta",
            "muy_alta",
        ],
    )

    if salida.isna().any().any():
        raise ValueError(
            "El indice contiene valores faltantes."
        )

    salida = salida.sort_values(
        "km_inicio"
    ).reset_index(drop=True)

    salida.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("\n=== PARAMETROS NORMALIZACION ===")
    for variable, p05, p95 in parametros:
        print(
            f"{variable}: "
            f"P05={p05:.6f} | "
            f"P95={p95:.6f}"
        )

    print("\n=== RESULTADO ===")
    print("Filas:", len(salida))
    print(
        "Faltantes:",
        int(salida.isna().sum().sum()),
    )

    print(
        "Indice min:",
        round(salida["indice_exposicion"].min(), 2),
    )
    print(
        "Indice medio:",
        round(salida["indice_exposicion"].mean(), 2),
    )
    print(
        "Indice max:",
        round(salida["indice_exposicion"].max(), 2),
    )

    print("\n=== TOP 15 SEGMENTOS ===")

    top = (
        salida.sort_values(
            "indice_exposicion",
            ascending=False,
        )
        .head(15)
    )

    print(
        top[
            [
                "ranking_exposicion",
                "km_inicio",
                "km_fin",
                "subindice_topografia",
                "subindice_hidrologia",
                "subindice_clima",
                "indice_exposicion",
                "clase_exposicion",
            ]
        ].to_string(index=False)
    )

    print(
        "\nArchivo:",
        OUTPUT_FILE.relative_to(ROOT),
    )


if __name__ == "__main__":
    main()
