"""Genera un change-control V2 exclusivamente demostrativo y simulado.

Los datos producidos no describen el estado real del corredor y no pueden
utilizarse como evidencia operacional. La simulacion sirve para probar el
contrato, la trazabilidad y la deteccion determinista de cambios.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.segment.generar_grafo_segmentos_v2 import (
    DEFAULT_SOURCE,
    load_segment_keys,
    segment_id,
    write_atomic,
)


DEFAULT_CONFIG = ROOT / "config" / "v2_change_demo.json"
DEFAULT_SNAPSHOTS = (
    ROOT / "data" / "processed" / "v2" / "segment_evidence_snapshots.csv"
)
DEFAULT_EVENTS = ROOT / "data" / "processed" / "v2" / "segment_change_events.csv"

SNAPSHOT_FIELDS = [
    "segment_id",
    "km_inicio",
    "km_fin",
    "observed_at_utc",
    "ingested_at_utc",
    "metric_name",
    "metric_value",
    "unit",
    "evidence_type",
    "fuente",
    "source_version",
    "uncertainty_lower",
    "uncertainty_upper",
    "quality_flag",
    "is_simulated",
    "simulation_scenario_id",
    "notes",
]

EVENT_FIELDS = [
    "change_event_id",
    "segment_id",
    "baseline_snapshot_at_utc",
    "current_snapshot_at_utc",
    "metric_name",
    "baseline_value",
    "current_value",
    "delta_abs",
    "delta_pct",
    "change_direction",
    "change_class",
    "confidence",
    "is_simulated",
    "simulation_scenario_id",
    "fuente",
    "source_version",
]


class ChangeDemoContractError(ValueError):
    """Indica una configuracion o producto demostrativo invalido."""


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))

    if config.get("simulation_only") is not True:
        raise ChangeDemoContractError("La demo debe declarar simulation_only=true.")
    if config.get("operational_use_allowed") is not False:
        raise ChangeDemoContractError(
            "La demo debe declarar operational_use_allowed=false."
        )

    scenario_id = str(config.get("scenario_id", ""))
    source = str(config.get("provenance", {}).get("fuente", ""))
    if not scenario_id.startswith("demo_"):
        raise ChangeDemoContractError("scenario_id debe comenzar con 'demo_'.")
    if not source.startswith("simulation:"):
        raise ChangeDemoContractError("fuente debe comenzar con 'simulation:'.")

    timestamps = config.get("timestamps", {})
    baseline = _parse_utc(timestamps.get("baseline_at_utc"), "baseline_at_utc")
    current = _parse_utc(timestamps.get("current_at_utc"), "current_at_utc")
    ingested = _parse_utc(timestamps.get("ingested_at_utc"), "ingested_at_utc")
    if not baseline < current <= ingested:
        raise ChangeDemoContractError(
            "Se requiere baseline_at_utc < current_at_utc <= ingested_at_utc."
        )

    thresholds = config.get("change_thresholds_abs", {})
    ordered = [
        float(thresholds.get("stable_max", -1)),
        float(thresholds.get("minor_max", -1)),
        float(thresholds.get("moderate_max", -1)),
    ]
    if not 0 <= ordered[0] < ordered[1] < ordered[2]:
        raise ChangeDemoContractError("Los umbrales de cambio no son crecientes.")

    _validate_zones(config.get("demonstration_zones", []))
    return config


def _parse_utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ChangeDemoContractError(f"{field} debe ser ISO 8601 UTC terminado en Z.")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ChangeDemoContractError(f"{field} no es un timestamp valido.") from exc


def _validate_zones(zones: list[dict[str, Any]]) -> None:
    covered: set[int] = set()
    for zone in zones:
        start = int(zone["km_inicio_min"])
        end = int(zone["km_inicio_max"])
        if start < 0 or end > 129 or start > end:
            raise ChangeDemoContractError(f"Zona demostrativa invalida: {zone}.")
        zone_km = set(range(start, end + 1))
        if covered & zone_km:
            raise ChangeDemoContractError("Las zonas demostrativas no pueden solaparse.")
        covered.update(zone_km)


def _baseline_value(km_inicio: int, config: dict[str, Any]) -> float:
    formula = config["baseline_formula"]
    value = float(formula["intercept"]) + (
        (
            (km_inicio * int(formula["multiplier"]))
            % int(formula["modulus"])
        )
        - int(formula["center"])
    ) * float(formula["scale"])
    return round(value, 3)


def _delta_value(km_inicio: int, config: dict[str, Any]) -> float:
    for zone in config["demonstration_zones"]:
        if int(zone["km_inicio_min"]) <= km_inicio <= int(zone["km_inicio_max"]):
            return float(zone["delta"])
    pattern = [float(value) for value in config["default_delta_pattern"]]
    return pattern[km_inicio % len(pattern)]


def _change_class(delta: float, config: dict[str, Any]) -> str:
    absolute = abs(delta)
    thresholds = config["change_thresholds_abs"]
    if absolute <= float(thresholds["stable_max"]):
        return "stable"
    if absolute <= float(thresholds["minor_max"]):
        return "minor"
    if absolute <= float(thresholds["moderate_max"]):
        return "moderate"
    return "major"


def _change_direction(delta: float, config: dict[str, Any]) -> str:
    stable_max = float(config["change_thresholds_abs"]["stable_max"])
    if abs(delta) <= stable_max:
        return "stable"
    return "increase" if delta > 0 else "decrease"


def build_demo(
    config: dict[str, Any],
    source: Path = DEFAULT_SOURCE,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Construye snapshots y eventos simulados para las 130 claves V1."""

    keys = load_segment_keys(source)
    timestamps = config["timestamps"]
    provenance = config["provenance"]
    metric = config["metric"]
    scenario_id = str(config["scenario_id"])
    version = str(config["schema_version"])
    uncertainty = config["uncertainty_half_width"]

    snapshots: list[dict[str, object]] = []
    events: list[dict[str, object]] = []

    for km_inicio, km_fin in keys:
        identity = segment_id(km_inicio, km_fin)
        baseline = _baseline_value(km_inicio, config)
        current = round(baseline + _delta_value(km_inicio, config), 3)
        values = [
            (
                timestamps["baseline_at_utc"],
                baseline,
                float(uncertainty["baseline"]),
            ),
            (
                timestamps["current_at_utc"],
                current,
                float(uncertainty["current"]),
            ),
        ]

        for observed_at, value, half_width in values:
            snapshots.append(
                {
                    "segment_id": identity,
                    "km_inicio": km_inicio,
                    "km_fin": km_fin,
                    "observed_at_utc": observed_at,
                    "ingested_at_utc": timestamps["ingested_at_utc"],
                    "metric_name": metric["name"],
                    "metric_value": f"{value:.3f}",
                    "unit": metric["unit"],
                    "evidence_type": "simulated",
                    "fuente": provenance["fuente"],
                    "source_version": version,
                    "uncertainty_lower": f"{value - half_width:.3f}",
                    "uncertainty_upper": f"{value + half_width:.3f}",
                    "quality_flag": provenance["quality_flag"],
                    "is_simulated": "true",
                    "simulation_scenario_id": scenario_id,
                    "notes": provenance["notes"],
                }
            )

        delta = round(current - baseline, 3)
        delta_pct = round((delta / baseline) * 100.0, 6)
        events.append(
            {
                "change_event_id": (
                    f"chg_{scenario_id}_{identity}_{metric['name']}"
                ),
                "segment_id": identity,
                "baseline_snapshot_at_utc": timestamps["baseline_at_utc"],
                "current_snapshot_at_utc": timestamps["current_at_utc"],
                "metric_name": metric["name"],
                "baseline_value": f"{baseline:.3f}",
                "current_value": f"{current:.3f}",
                "delta_abs": f"{delta:.3f}",
                "delta_pct": f"{delta_pct:.6f}",
                "change_direction": _change_direction(delta, config),
                "change_class": _change_class(delta, config),
                "confidence": "0.0",
                "is_simulated": "true",
                "simulation_scenario_id": scenario_id,
                "fuente": provenance["fuente"],
                "source_version": version,
            }
        )

    validate_demo(snapshots, events, config)
    return snapshots, events


def validate_demo(
    snapshots: list[dict[str, object]],
    events: list[dict[str, object]],
    config: dict[str, Any],
) -> None:
    """Impide publicar una demo incompleta o confundible con evidencia real."""

    if len(snapshots) != 260 or len(events) != 130:
        raise ChangeDemoContractError("La demo requiere 260 snapshots y 130 eventos.")

    scenario_id = str(config["scenario_id"])
    all_rows = snapshots + events
    for row in all_rows:
        if row.get("is_simulated") != "true":
            raise ChangeDemoContractError("Toda fila debe marcar is_simulated=true.")
        if row.get("simulation_scenario_id") != scenario_id:
            raise ChangeDemoContractError("Toda fila debe conservar scenario_id.")
        if not str(row.get("fuente", "")).startswith("simulation:"):
            raise ChangeDemoContractError("Toda fuente debe identificarse como simulacion.")

    if any(row["evidence_type"] != "simulated" for row in snapshots):
        raise ChangeDemoContractError("Todo snapshot debe ser simulated.")
    if any(float(row["confidence"]) != 0.0 for row in events):
        raise ChangeDemoContractError(
            "La confianza operacional de eventos simulados debe ser 0.0."
        )


def render_csv(rows: Iterable[dict[str, object]], fields: list[str]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def generate(
    config_path: Path = DEFAULT_CONFIG,
    source: Path = DEFAULT_SOURCE,
) -> tuple[str, str]:
    config = load_config(config_path)
    snapshots, events = build_demo(config, source)
    return (
        render_csv(snapshots, SNAPSHOT_FIELDS),
        render_csv(events, EVENT_FIELDS),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--snapshots-output", type=Path, default=DEFAULT_SNAPSHOTS)
    parser.add_argument("--events-output", type=Path, default=DEFAULT_EVENTS)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifica que ambos productos coincidan con la regeneracion.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshots, events = generate(args.config, args.source)
    outputs = {
        args.snapshots_output: snapshots,
        args.events_output: events,
    }

    if args.check:
        for path, expected in outputs.items():
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                raise SystemExit(f"ERROR: {path} no coincide con su regeneracion.")
        print("OK: demo change-control coincide con la regeneracion determinista.")
        return 0

    for path, content in outputs.items():
        write_atomic(path, content)
    print("OK: 260 snapshots y 130 eventos SIMULADOS generados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
