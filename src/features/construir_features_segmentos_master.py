from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

BASE_FILE = ROOT / "data" / "processed" / "segmentos.csv"

FUENTES = {
    "elevacion": ROOT / "data" / "processed" / "topografia" / "features_elevacion_segmentos.csv",
    "pendiente_longitudinal": ROOT / "data" / "processed" / "topografia" / "features_pendiente_longitudinal.csv",
    "terreno": ROOT / "data" / "processed" / "topografia" / "features_terreno_segmentos.csv",
    "hidrologia": ROOT / "data" / "processed" / "topografia" / "features_hidrologia_segmentos.csv",
    "clima": ROOT / "data" / "processed" / "clima" / "features_clima_segmentos.csv",
}

OUT_FILE = ROOT / "data" / "processed" / "features_segmentos_master.csv"

KEYS = ["km_inicio", "km_fin"]


def validar_tabla(df, nombre):
    faltan = [c for c in KEYS if c not in df.columns]

    if faltan:
        raise ValueError(
            f"{nombre}: faltan claves {faltan}"
        )

    if len(df) != 130:
        raise ValueError(
            f"{nombre}: se esperaban 130 filas y hay {len(df)}"
        )

    if df.duplicated(KEYS).any():
        raise ValueError(
            f"{nombre}: existen segmentos duplicados"
        )


def main():
    base = pd.read_csv(BASE_FILE)
    validar_tabla(base, "segmentos")

    master = base.copy()

    print("=== TABLA MAESTRA DE FEATURES ===")
    print("Base:", len(master), "segmentos")

    for nombre, archivo in FUENTES.items():
        df = pd.read_csv(archivo)
        validar_tabla(df, nombre)

        columnas_nuevas = [
            c for c in df.columns
            if c not in KEYS
        ]

        solapadas = [
            c for c in columnas_nuevas
            if c in master.columns
        ]

        if solapadas:
            raise ValueError(
                f"{nombre}: columnas ya existentes: {solapadas}"
            )

        master = master.merge(
            df,
            on=KEYS,
            how="left",
            validate="one_to_one",
        )

        print(
            f"{nombre}: +{len(columnas_nuevas)} columnas"
            f" -> {len(master.columns)} totales"
        )

    if len(master) != 130:
        raise ValueError(
            f"Merge final incorrecto: {len(master)} filas"
        )

    faltantes = master.isna().sum()
    faltantes = faltantes[faltantes > 0]

    if not faltantes.empty:
        raise ValueError(
            "La tabla maestra contiene faltantes:\n"
            + faltantes.to_string()
        )

    master = master.sort_values(
        ["km_inicio", "km_fin"]
    ).reset_index(drop=True)

    OUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    master.to_csv(
        OUT_FILE,
        index=False,
    )

    numericas = master.select_dtypes(
        include="number"
    ).columns.tolist()

    print("\n=== RESULTADO ===")
    print("Filas:", len(master))
    print("Columnas:", len(master.columns))
    print("Columnas numericas:", len(numericas))
    print("Faltantes:", int(master.isna().sum().sum()))

    print("\nColumnas:")
    for c in master.columns:
        print("-", c)

    print(
        "\nArchivo:",
        OUT_FILE.relative_to(ROOT),
    )


if __name__ == "__main__":
    main()
