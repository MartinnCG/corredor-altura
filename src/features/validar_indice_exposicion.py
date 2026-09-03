from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

INDICE_FILE = (
    ROOT / "data" / "processed" /
    "indice_exposicion_segmentos.csv"
)

EVIDENCIA_FILE = (
    ROOT / "data" / "processed" /
    "evidencia_operacional_segmentos.csv"
)

OUT_FILE = (
    ROOT / "data" / "processed" /
    "validacion_indice_exposicion.csv"
)


def comparar_dimension(df, subindice, campo):
    con = df.loc[df[campo] == 1, subindice]
    sin = df.loc[df[campo] == 0, subindice]

    return {
        "dimension": campo.replace("campo_", ""),
        "subindice": subindice,
        "n_con_evidencia": len(con),
        "n_sin_evidencia": len(sin),
        "media_con": con.mean(),
        "media_sin": sin.mean(),
        "mediana_con": con.median(),
        "mediana_sin": sin.median(),
        "diferencia_media": con.mean() - sin.mean(),
    }


def main():
    indice = pd.read_csv(INDICE_FILE)
    evidencia = pd.read_csv(EVIDENCIA_FILE)

    df = indice.merge(
        evidencia,
        on=["km_inicio", "km_fin"],
        how="inner",
        validate="one_to_one",
    )

    if len(df) != 130:
        raise ValueError(
            f"Se esperaban 130 segmentos y hay {len(df)}."
        )

    print("=== ETAPA 4 — VALIDACION INDEPENDIENTE ===")
    print("Segmentos:", len(df))

    print("\n=== INDICE SEGUN NIVEL OPERACIONAL ===")

    resumen_nivel = (
        df.groupby(
            "nivel_campo_max",
            dropna=False,
            observed=False,
        )["indice_exposicion"]
        .agg(["count", "mean", "median", "min", "max"])
        .sort_values("mean", ascending=False)
    )

    print(resumen_nivel.to_string())

    comparaciones = [
        comparar_dimension(
            df,
            "subindice_hidrologia",
            "campo_hidrologico",
        ),
        comparar_dimension(
            df,
            "subindice_topografia",
            "campo_topografico",
        ),
        comparar_dimension(
            df,
            "subindice_clima",
            "campo_climatico",
        ),
    ]

    comp = pd.DataFrame(comparaciones)

    print("\n=== VALIDACION POR DIMENSION ===")
    print(
        comp.to_string(
            index=False,
            float_format=lambda x: f"{x:.3f}",
        )
    )

    # Evidencia correspondiente a cualquiera de las
    # tres dimensiones incluidas en el modelo.
    df["evidencia_modelada"] = (
        (df["campo_hidrologico"] == 1)
        | (df["campo_topografico"] == 1)
        | (df["campo_climatico"] == 1)
    ).astype(int)

    orden = df.sort_values(
        "indice_exposicion",
        ascending=False,
    ).reset_index(drop=True)

    print("\n=== CAPTURA EN SEGMENTOS DE MAYOR EXPOSICION ===")

    for n in [13, 26]:
        top = orden.head(n)

        proporcion = (
            top["evidencia_modelada"].mean() * 100
        )

        print(
            f"Top {n:>2} segmentos: "
            f"{proporcion:.1f}% con evidencia "
            f"hidrologica/topografica/climatica"
        )

    muy_alta = df[
        df["clase_exposicion"] == "muy_alta"
    ]

    print(
        "Clase muy_alta:",
        f"{muy_alta['evidencia_modelada'].mean() * 100:.1f}%",
        "con evidencia modelada",
    )

    columnas_out = [
        "km_inicio",
        "km_fin",
        "indice_exposicion",
        "ranking_exposicion",
        "clase_exposicion",
        "subindice_topografia",
        "subindice_hidrologia",
        "subindice_clima",
        "n_peligros_campo",
        "nivel_campo_max",
        "campo_hidrologico",
        "campo_topografico",
        "campo_climatico",
        "evidencia_modelada",
        "peligros_campo",
    ]

    df[columnas_out].to_csv(
        OUT_FILE,
        index=False,
    )

    print("\n=== TOP 15 + EVIDENCIA ===")

    print(
        orden[
            [
                "ranking_exposicion",
                "km_inicio",
                "km_fin",
                "indice_exposicion",
                "nivel_campo_max",
                "campo_hidrologico",
                "campo_topografico",
                "campo_climatico",
                "peligros_campo",
            ]
        ]
        .head(15)
        .to_string(index=False)
    )

    print(
        "\nArchivo:",
        OUT_FILE.relative_to(ROOT),
    )


if __name__ == "__main__":
    main()
