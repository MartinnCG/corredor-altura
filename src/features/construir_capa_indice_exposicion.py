from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

SEGMENTOS_FILE = (
    ROOT / "data" / "processed" /
    "segmentos.geojson"
)

INDICE_FILE = (
    ROOT / "data" / "processed" /
    "indice_exposicion_segmentos.csv"
)

OUTPUT_FILE = (
    ROOT / "data" / "processed" /
    "segmentos_indice_exposicion.geojson"
)


def main():
    segmentos = gpd.read_file(SEGMENTOS_FILE)
    indice = pd.read_csv(INDICE_FILE)

    print("=== CAPA ESPACIAL DE EXPOSICION ===")
    print("Segmentos geometria:", len(segmentos))
    print("Segmentos indice:", len(indice))

    if len(segmentos) != 130:
        raise ValueError(
            f"Se esperaban 130 geometrías y hay {len(segmentos)}."
        )

    if len(indice) != 130:
        raise ValueError(
            f"Se esperaban 130 índices y hay {len(indice)}."
        )

    columnas_indice = [
        "km_inicio",
        "km_fin",
        "subindice_topografia",
        "subindice_hidrologia",
        "subindice_clima",
        "indice_exposicion",
        "ranking_exposicion",
        "clase_exposicion",
    ]

    faltantes = [
        c for c in columnas_indice
        if c not in indice.columns
    ]

    if faltantes:
        raise ValueError(
            f"Faltan columnas del índice: {faltantes}"
        )

    # Eliminar posibles columnas duplicadas antes del join,
    # conservando las claves km_inicio / km_fin.
    columnas_reemplazar = [
        c for c in columnas_indice
        if c not in ["km_inicio", "km_fin"]
        and c in segmentos.columns
    ]

    if columnas_reemplazar:
        segmentos = segmentos.drop(
            columns=columnas_reemplazar
        )

    salida = segmentos.merge(
        indice[columnas_indice],
        on=["km_inicio", "km_fin"],
        how="left",
        validate="one_to_one",
    )

    if len(salida) != 130:
        raise ValueError(
            f"El join produjo {len(salida)} segmentos."
        )

    if salida["indice_exposicion"].isna().any():
        n = int(
            salida["indice_exposicion"]
            .isna()
            .sum()
        )
        raise ValueError(
            f"Hay {n} segmentos sin índice."
        )

    salida.to_file(
        OUTPUT_FILE,
        driver="GeoJSON",
    )

    print("\nCRS:", salida.crs)
    print("Filas:", len(salida))
    print(
        "Indice faltante:",
        int(
            salida["indice_exposicion"]
            .isna()
            .sum()
        ),
    )

    print("\nClases:")
    print(
        salida["clase_exposicion"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nTop 10 espacial:")
    print(
        salida[
            [
                "ranking_exposicion",
                "km_inicio",
                "km_fin",
                "indice_exposicion",
                "clase_exposicion",
            ]
        ]
        .sort_values("ranking_exposicion")
        .head(10)
        .to_string(index=False)
    )

    print(
        "\nArchivo:",
        OUTPUT_FILE.relative_to(ROOT),
    )


if __name__ == "__main__":
    main()
