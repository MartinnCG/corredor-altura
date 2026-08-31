from pathlib import Path

import rasterio
from rasterio.merge import merge


ROOT = Path(__file__).resolve().parents[3]

DEM_DIR = ROOT / "data" / "external" / "dem"
OUT_DIR = ROOT / "data" / "processed" / "topografia"
OUT_FILE = OUT_DIR / "dem_mdear_30m_mosaico.tif"


def main():
    archivos = sorted(DEM_DIR.glob("*/*.img"))

    if not archivos:
        raise FileNotFoundError(
            f"No se encontraron archivos .img en {DEM_DIR}"
        )

    print("=== PREPARACION DEM MDE-Ar 30 m ===")
    print(f"Hojas encontradas: {len(archivos)}")

    for archivo in archivos:
        print(f" - {archivo.relative_to(ROOT)}")

    datasets = [rasterio.open(archivo) for archivo in archivos]

    try:
        mosaico, transform = merge(datasets)

        perfil = datasets[0].profile.copy()
        perfil.update(
            driver="GTiff",
            height=mosaico.shape[1],
            width=mosaico.shape[2],
            transform=transform,
            count=1,
            compress="deflate",
            tiled=True,
        )

        OUT_DIR.mkdir(parents=True, exist_ok=True)

        with rasterio.open(OUT_FILE, "w", **perfil) as dst:
            dst.write(mosaico)

    finally:
        for ds in datasets:
            ds.close()

    with rasterio.open(OUT_FILE) as src:
        arr = src.read(1, masked=True)

        print("\nResultado:")
        print("Archivo:", OUT_FILE.relative_to(ROOT))
        print("CRS:", src.crs)
        print("Resolucion:", src.res)
        print("Tamaño:", src.width, "x", src.height)
        print("Bounds:", src.bounds)
        print("NoData:", src.nodata)
        print("Elevacion min:", float(arr.min()))
        print("Elevacion max:", float(arr.max()))


if __name__ == "__main__":
    main()
