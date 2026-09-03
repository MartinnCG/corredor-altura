from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT / "data" / "processed" /
    "indice_exposicion_segmentos.csv"
)

OUTPUT_DIR = ROOT / "outputs" / "figuras"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = (
    OUTPUT_DIR /
    "perfil_longitudinal_indice_exposicion.png"
)


def main():
    df = pd.read_csv(INPUT_FILE)

    if len(df) != 130:
        raise ValueError(
            f"Se esperaban 130 segmentos y hay {len(df)}."
        )

    x = (df["km_inicio"] + df["km_fin"]) / 2

    fig, ax = plt.subplots(figsize=(14, 7))

    # Indice compuesto.
    ax.plot(
        x,
        df["indice_exposicion"],
        linewidth=2.2,
        label="Índice compuesto",
    )

    # Subindices convertidos a escala 0-100.
    ax.plot(
        x,
        df["subindice_topografia"] * 100,
        linewidth=1.2,
        alpha=0.75,
        label="Topografía",
    )

    ax.plot(
        x,
        df["subindice_hidrologia"] * 100,
        linewidth=1.2,
        alpha=0.75,
        label="Hidrología",
    )

    ax.plot(
        x,
        df["subindice_clima"] * 100,
        linewidth=1.2,
        alpha=0.75,
        label="Clima",
    )

    ax.set_title(
        "Perfil longitudinal de exposición — Corredor de Altura",
        fontsize=14,
    )

    ax.set_xlabel("Progresiva operacional (km)")
    ax.set_ylabel("Exposición relativa (0–100)")

    ax.set_xlim(0, 130)
    ax.set_ylim(0, 105)

    ax.set_xticks(range(0, 131, 10))

    ax.grid(
        True,
        alpha=0.25,
    )

    ax.legend(
        loc="upper left",
        ncol=4,
    )

    # Destacar los 10 segmentos con mayor índice.
    top10 = df.nsmallest(
        10,
        "ranking_exposicion",
    )

    for _, row in top10.iterrows():
        centro = (
            row["km_inicio"] + row["km_fin"]
        ) / 2

        ax.scatter(
            centro,
            row["indice_exposicion"],
            s=28,
            zorder=5,
        )

    texto = (
        "Índice compuesto = ⅓ Topografía + "
        "⅓ Hidrología + ⅓ Clima\n"
        "Clasificación relativa entre 130 segmentos de 1 km"
    )

    ax.text(
        0.99,
        0.02,
        texto,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        alpha=0.8,
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_FILE,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)

    print("=== PERFIL LONGITUDINAL ===")
    print("Segmentos:", len(df))
    print(
        "Indice min:",
        round(df["indice_exposicion"].min(), 2),
    )
    print(
        "Indice max:",
        round(df["indice_exposicion"].max(), 2),
    )
    print("Figura:", OUTPUT_FILE.relative_to(ROOT))

    print("\nTop 10 señalados:")
    print(
        top10[
            [
                "ranking_exposicion",
                "km_inicio",
                "km_fin",
                "indice_exposicion",
            ]
        ]
        .sort_values("ranking_exposicion")
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
