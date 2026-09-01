from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import shape
from pysheds.grid import Grid
from pysheds.sview import Raster, ViewFinder


ROOT = Path(__file__).resolve().parents[3]

FDR = ROOT / "data" / "processed" / "topografia" / "flow_direction.tif"
ACC = ROOT / "data" / "processed" / "topografia" / "flow_accumulation.tif"

OUT_SEC = ROOT / "data" / "processed" / "topografia" / "drenajes_secundarios.geojson"
OUT_PRI = ROOT / "data" / "processed" / "topografia" / "drenajes_principales.geojson"

DMAP = (64, 128, 1, 2, 4, 8, 16, 32)

CRS = "EPSG:32719"

UMBRAL_SEC = 2500
UMBRAL_PRI = 10000


def crear_mascara(acc, umbral):
    arr = (np.asarray(acc) >= umbral).astype("uint8")

    vf = ViewFinder(
        affine=acc.viewfinder.affine,
        shape=acc.viewfinder.shape,
        nodata=0,
        crs=acc.viewfinder.crs,
        mask=acc.viewfinder.mask,
    )

    return Raster(
        arr,
        viewfinder=vf,
    )


def guardar_red(red, path, tipo, umbral):
    geoms = [shape(f["geometry"]) for f in red["features"]]

    gdf = gpd.GeoDataFrame(
        {
            "tipo_drenaje": [tipo] * len(geoms),
            "umbral_celdas": [umbral] * len(geoms),
        },
        geometry=geoms,
        crs=CRS,
    )

    gdf.to_file(path, driver="GeoJSON")


def main():
    grid = Grid.from_raster(str(FDR))

    fdir = grid.read_raster(str(FDR))
    acc = grid.read_raster(str(ACC))

    mask_sec = crear_mascara(acc, UMBRAL_SEC)
    mask_pri = crear_mascara(acc, UMBRAL_PRI)

    red_sec = grid.extract_river_network(
        fdir,
        mask_sec,
        dirmap=DMAP,
    )

    red_pri = grid.extract_river_network(
        fdir,
        mask_pri,
        dirmap=DMAP,
    )

    guardar_red(
        red_sec,
        OUT_SEC,
        "secundario",
        UMBRAL_SEC,
    )

    guardar_red(
        red_pri,
        OUT_PRI,
        "principal",
        UMBRAL_PRI,
    )

    print("=== RED DE DRENAJES ===")
    print("Secundarios:", len(red_sec["features"]))
    print("Principales:", len(red_pri["features"]))
    print("CRS:", CRS)


if __name__ == "__main__":
    main()
