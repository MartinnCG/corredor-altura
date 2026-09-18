"""Calcula estadistica espacial V2 sobre el change-control simulado.

La salida es exclusivamente demostrativa: prueba autocorrelacion global y
local sobre el grafo lineal validado, pero no describe condiciones reales.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import numpy as np
    from esda import Geary, Moran, Moran_Local
    from libpysal.weights import W
    from libpysal.weights.spatial_lag import lag_spatial
    from scipy.stats import false_discovery_control
except ImportError as exc:  # pragma: no cover - mensaje de instalacion
    raise SystemExit(
        "ERROR: faltan dependencias V2. Instalar con "
        "'python -m pip install -r requirements-v2.txt'."
    ) from exc

from src.segment.generar_grafo_segmentos_v2 import (
    DEFAULT_OUTPUT as DEFAULT_NEIGHBORS,
    EXPECTED_KEYS,
    segment_id,
    write_atomic,
)


DEFAULT_CONFIG = ROOT / "config" / "v2_spatial_statistics.json"
DEFAULT_EVENTS = ROOT / "data" / "processed" / "v2" / "segment_change_events.csv"
DEFAULT_LOCAL_OUTPUT = ROOT / "data" / "processed" / "v2" / "segment_local_moran.csv"
DEFAULT_SUMMARY_OUTPUT = (
    ROOT / "data" / "processed" / "v2" / "spatial_statistics_summary.json"
)

LOCAL_FIELDS = [
    "segment_id",
    "km_inicio",
    "km_fin",
    "metric_name",
    "metric_value",
    "spatial_lag_z",
    "local_moran_i",
    "p_sim",
    "p_fdr_bh",
    "significant_fdr",
    "lisa_quadrant",
    "lisa_cluster_fdr",
    "permutations",
    "weights_id",
    "is_simulated",
    "simulation_scenario_id",
    "fuente",
    "source_version",
    "notes",
]

QUADRANTS = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}


class SpatialStatisticsContractError(ValueError):
    """Indica que entradas, configuracion o resultados violan el contrato."""


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("simulation_only") is not True:
        raise SpatialStatisticsContractError("Se requiere simulation_only=true.")
    if config.get("operational_use_allowed") is not False:
        raise SpatialStatisticsContractError(
            "Se requiere operational_use_allowed=false."
        )

    inference = config.get("inference", {})
    permutations = int(inference.get("permutations", 0))
    alpha = float(inference.get("alpha", -1))
    if permutations < 99:
        raise SpatialStatisticsContractError("Se requieren al menos 99 permutaciones.")
    if not 0 < alpha < 1:
        raise SpatialStatisticsContractError("alpha debe estar entre 0 y 1.")
    if inference.get("multiple_testing") != "fdr_bh":
        raise SpatialStatisticsContractError("La correccion local debe ser fdr_bh.")

    transforms = {
        str(config["weights"]["primary_transformation"]).lower(),
        str(config["weights"]["sensitivity_transformation"]).lower(),
    }
    if transforms != {"r", "b"}:
        raise SpatialStatisticsContractError(
            "La demo debe comparar pesos row-standardized (r) y binarios (b)."
        )
    return config


def load_neighbors(path: Path = DEFAULT_NEIGHBORS) -> tuple[list[str], dict[str, list[str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if len(rows) != 258:
        raise SpatialStatisticsContractError("Se esperaban 258 aristas dirigidas.")

    ids = [segment_id(*key) for key in EXPECTED_KEYS]
    neighbors = {identity: [] for identity in ids}
    edges: set[tuple[str, str]] = set()
    for row in rows:
        origin = row["segment_id"]
        neighbor = row["neighbor_segment_id"]
        if origin not in neighbors or neighbor not in neighbors:
            raise SpatialStatisticsContractError("El grafo contiene una identidad desconocida.")
        edge = (origin, neighbor)
        if edge in edges:
            raise SpatialStatisticsContractError(f"Arista duplicada: {edge}.")
        edges.add(edge)
        neighbors[origin].append(neighbor)

    if any((neighbor, origin) not in edges for origin, neighbor in edges):
        raise SpatialStatisticsContractError("El grafo no es reciproco.")
    if any(not adjacent for adjacent in neighbors.values()):
        raise SpatialStatisticsContractError("El grafo contiene islas.")
    return ids, neighbors


def load_events(
    ids: list[str],
    config: dict[str, Any],
    path: Path = DEFAULT_EVENTS,
) -> tuple[np.ndarray, str]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if len(rows) != 130:
        raise SpatialStatisticsContractError("Se esperaban 130 eventos de cambio.")
    indexed = {row["segment_id"]: row for row in rows}
    if set(indexed) != set(ids) or len(indexed) != 130:
        raise SpatialStatisticsContractError("Los eventos no cubren los 130 segmentos.")

    metric = str(config["metric_name"])
    value_field = str(config["value_field"])
    scenarios = {row["simulation_scenario_id"] for row in rows}
    if len(scenarios) != 1:
        raise SpatialStatisticsContractError("Los eventos deben pertenecer a un escenario.")

    for row in rows:
        if row["metric_name"] != metric:
            raise SpatialStatisticsContractError("La metrica no coincide con la configuracion.")
        if row["is_simulated"].lower() != "true":
            raise SpatialStatisticsContractError("Toda entrada debe ser simulada.")
        if not row["fuente"].startswith("simulation:"):
            raise SpatialStatisticsContractError("Toda fuente de entrada debe ser simulada.")

    values = np.asarray([float(indexed[identity][value_field]) for identity in ids])
    if not np.isfinite(values).all() or np.allclose(values.std(), 0.0):
        raise SpatialStatisticsContractError("La variable debe ser finita y no constante.")
    return values, scenarios.pop()


def build_weights(ids: list[str], neighbors: dict[str, list[str]]) -> W:
    """Construye pesos PySAL manteniendo el orden canonico del corredor."""

    return W(neighbors, id_order=ids, silence_warnings=True)


def _global_statistics(
    values: np.ndarray,
    weights: W,
    transformation: str,
    permutations: int,
    seed: int,
) -> dict[str, Any]:
    np.random.seed(seed)
    moran = Moran(
        values,
        weights,
        transformation=transformation,
        permutations=permutations,
        two_tailed=True,
    )
    np.random.seed(seed)
    geary = Geary(
        values,
        weights,
        transformation=transformation,
        permutations=permutations,
    )
    return {
        "transformation": transformation,
        "moran_i": _rounded(moran.I),
        "moran_expected": _rounded(moran.EI),
        "moran_p_sim": _rounded(moran.p_sim),
        "geary_c": _rounded(geary.C),
        "geary_expected": _rounded(geary.EC),
        "geary_p_sim": _rounded(geary.p_sim),
        "permutations": permutations,
        "seed": seed,
    }


def _rounded(value: float) -> float:
    return round(float(value), 10)


def analyze(
    config: dict[str, Any],
    neighbors_path: Path = DEFAULT_NEIGHBORS,
    events_path: Path = DEFAULT_EVENTS,
) -> tuple[list[dict[str, object]], dict[str, Any]]:
    ids, neighbors = load_neighbors(neighbors_path)
    values, scenario_id = load_events(ids, config, events_path)
    weights = build_weights(ids, neighbors)

    inference = config["inference"]
    permutations = int(inference["permutations"])
    alpha = float(inference["alpha"])
    primary_transform = str(config["weights"]["primary_transformation"]).lower()
    sensitivity_transform = str(
        config["weights"]["sensitivity_transformation"]
    ).lower()
    seeds = inference["seeds"]

    primary = _global_statistics(
        values,
        weights,
        primary_transform,
        permutations,
        int(seeds["primary_global"]),
    )
    sensitivity = _global_statistics(
        values,
        weights,
        sensitivity_transform,
        permutations,
        int(seeds["sensitivity_global"]),
    )

    local = Moran_Local(
        values,
        weights,
        transformation=primary_transform,
        permutations=permutations,
        geoda_quads=False,
        n_jobs=1,
        keep_simulations=False,
        seed=int(seeds["primary_local"]),
        alternative="two-sided",
    )
    adjusted = np.asarray(false_discovery_control(local.p_sim, method="bh"))
    lag_z = np.asarray(lag_spatial(local.w, local.z))

    provenance = config["provenance"]
    weights_id = f"{config['weights']['id']}_{primary_transform}"
    rows: list[dict[str, object]] = []
    for index, identity in enumerate(ids):
        quadrant = QUADRANTS[int(local.q[index])]
        significant = bool(adjusted[index] <= alpha)
        km_inicio, km_fin = EXPECTED_KEYS[index]
        rows.append(
            {
                "segment_id": identity,
                "km_inicio": km_inicio,
                "km_fin": km_fin,
                "metric_name": config["metric_name"],
                "metric_value": f"{values[index]:.6f}",
                "spatial_lag_z": f"{lag_z[index]:.10f}",
                "local_moran_i": f"{local.Is[index]:.10f}",
                "p_sim": f"{local.p_sim[index]:.10f}",
                "p_fdr_bh": f"{adjusted[index]:.10f}",
                "significant_fdr": str(significant).lower(),
                "lisa_quadrant": quadrant,
                "lisa_cluster_fdr": quadrant if significant else "not_significant",
                "permutations": permutations,
                "weights_id": weights_id,
                "is_simulated": "true",
                "simulation_scenario_id": scenario_id,
                "fuente": provenance["fuente"],
                "source_version": config["schema_version"],
                "notes": provenance["notes"],
            }
        )

    cluster_counts = {
        label: sum(row["lisa_cluster_fdr"] == label for row in rows)
        for label in ["HH", "LH", "LL", "HL", "not_significant"]
    }
    summary = {
        "schema_version": config["schema_version"],
        "analysis_id": config["analysis_id"],
        "simulation_only": True,
        "operational_use_allowed": False,
        "simulation_scenario_id": scenario_id,
        "metric_name": config["metric_name"],
        "value_field": config["value_field"],
        "n_segments": len(ids),
        "weights_id": config["weights"]["id"],
        "primary": primary,
        "sensitivity": sensitivity,
        "local_inference": {
            "alpha": alpha,
            "multiple_testing": "fdr_bh",
            "alternative": "two-sided",
            "permutations": permutations,
            "seed": int(seeds["primary_local"]),
            "significant_raw": int(np.sum(local.p_sim <= alpha)),
            "significant_fdr": int(np.sum(adjusted <= alpha)),
            "cluster_counts_fdr": cluster_counts,
        },
        "software": {
            "esda": version("esda"),
            "libpysal": version("libpysal"),
            "numpy": version("numpy"),
            "scipy": version("scipy"),
        },
        "fuente": provenance["fuente"],
        "notes": provenance["notes"],
    }
    validate_results(rows, summary)
    return rows, summary


def validate_results(
    rows: list[dict[str, object]], summary: dict[str, Any]
) -> None:
    if len(rows) != 130:
        raise SpatialStatisticsContractError("Se requieren 130 resultados locales.")
    if summary["simulation_only"] is not True:
        raise SpatialStatisticsContractError("El resumen debe permanecer simulado.")

    identities = [str(row["segment_id"]) for row in rows]
    if identities != [segment_id(*key) for key in EXPECTED_KEYS]:
        raise SpatialStatisticsContractError("El orden local no es canonico.")
    for row in rows:
        if row["is_simulated"] != "true":
            raise SpatialStatisticsContractError("Toda salida local debe ser simulada.")
        if float(row["p_fdr_bh"]) + 1e-12 < float(row["p_sim"]):
            raise SpatialStatisticsContractError("p_fdr_bh no puede ser menor que p_sim.")
        significant = row["significant_fdr"] == "true"
        if significant != (row["lisa_cluster_fdr"] != "not_significant"):
            raise SpatialStatisticsContractError("Cluster y significancia no coinciden.")


def render_csv(rows: Iterable[dict[str, object]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=LOCAL_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def render_summary(summary: dict[str, Any]) -> str:
    return json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def generate(
    config_path: Path = DEFAULT_CONFIG,
    neighbors_path: Path = DEFAULT_NEIGHBORS,
    events_path: Path = DEFAULT_EVENTS,
) -> tuple[str, str]:
    config = load_config(config_path)
    rows, summary = analyze(config, neighbors_path, events_path)
    return render_csv(rows), render_summary(summary)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--neighbors", type=Path, default=DEFAULT_NEIGHBORS)
    parser.add_argument("--events", type=Path, default=DEFAULT_EVENTS)
    parser.add_argument("--local-output", type=Path, default=DEFAULT_LOCAL_OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    local_csv, summary_json = generate(args.config, args.neighbors, args.events)
    outputs = {
        args.local_output: local_csv,
        args.summary_output: summary_json,
    }
    if args.check:
        for path, expected in outputs.items():
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                raise SystemExit(f"ERROR: {path} no coincide con su regeneracion.")
        print("OK: estadistica espacial V2 coincide con la regeneracion.")
        return 0

    for path, content in outputs.items():
        write_atomic(path, content)
    print("OK: Moran, Geary y LISA simulados generados para 130 segmentos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
