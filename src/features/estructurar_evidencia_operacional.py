from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

PELIGROS = ROOT / "data" / "raw" / "peligros_operacionales_corredor.csv"
SEGMENTOS = ROOT / "data" / "processed" / "segmentos.csv"

SALIDA = (
    ROOT
    / "data"
    / "processed"
    / "evidencia_operacional_segmentos.csv"
)

CATEGORIAS = [
    "hidrologico",
    "climatico",
    "topografico",
    "geologico",
    "altitudinal",
    "operacional",
    "fauna",
]

ORDEN_NIVEL = {
    "medio": 1,
    "alto_medio": 2,
    "alto": 3,
}


def nivel_maximo(series):
    valores = [v for v in series.dropna() if v in ORDEN_NIVEL]

    if not valores:
        return None

    return max(valores, key=lambda x: ORDEN_NIVEL[x])


def main():
    peligros = pd.read_csv(PELIGROS)
    segmentos = pd.read_csv(SEGMENTOS)

    filas = []

    for _, seg in segmentos.iterrows():
        km_ini = float(seg["km_inicio"])
        km_fin = float(seg["km_fin"])

        # Solapamiento de intervalos [inicio, fin)
        aplican = peligros[
            (peligros["km_inicio"] < km_fin)
            & (peligros["km_fin"] > km_ini)
        ].copy()

        fila = {
            "km_inicio": int(km_ini),
            "km_fin": int(km_fin),
            "n_peligros_campo": int(len(aplican)),
            "nivel_campo_max": nivel_maximo(aplican["nivel"]),
        }

        for categoria in CATEGORIAS:
            subset = aplican[aplican["categoria"] == categoria]

            fila[f"campo_{categoria}"] = int(len(subset) > 0)
            fila[f"n_{categoria}_campo"] = int(len(subset))

        fila["peligros_campo"] = (
            "|".join(sorted(aplican["peligro"].unique()))
            if len(aplican)
            else ""
        )

        fila["estacionalidades_campo"] = (
            "|".join(sorted(aplican["estacionalidad"].unique()))
            if len(aplican)
            else ""
        )

        filas.append(fila)

    df = pd.DataFrame(filas)

    df.to_csv(SALIDA, index=False)

    print("=== EVIDENCIA OPERACIONAL POR SEGMENTO ===")
    print("Segmentos:", len(df))
    print("Segmentos sin peligros:", int((df["n_peligros_campo"] == 0).sum()))

    print("\nNivel maximo:")
    print(df["nivel_campo_max"].value_counts(dropna=False))

    print("\nPresencia por categoria:")
    for categoria in CATEGORIAS:
        col = f"campo_{categoria}"
        print(
            f"{categoria:12s}: "
            f"{int(df[col].sum()):3d} segmentos"
        )

    print("\nNumero de peligros por segmento:")
    print(df["n_peligros_campo"].describe())

    print("\nMuestra:")
    cols = [
        "km_inicio",
        "km_fin",
        "n_peligros_campo",
        "nivel_campo_max",
        "campo_hidrologico",
        "campo_climatico",
        "campo_topografico",
        "campo_geologico",
        "campo_altitudinal",
    ]

    print(df[cols].head(35).to_string(index=False))

    print("\nArchivo:", SALIDA.relative_to(ROOT))


if __name__ == "__main__":
    main()
