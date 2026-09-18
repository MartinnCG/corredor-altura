"""Genera el grafo lineal V2 a partir de los segmentos congelados de V1.

El modulo usa solamente la identidad longitudinal ``(km_inicio, km_fin)``.
No modifica, recalcula ni interpreta ningun producto analitico de V1.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import tempfile
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "data" / "processed" / "segmentos.csv"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "v2" / "segment_neighbors.csv"

EXPECTED_KEYS = [(km, km + 1) for km in range(130)]
FIELDNAMES = [
    "segment_id",
    "km_inicio",
    "km_fin",
    "neighbor_segment_id",
    "neighbor_km_inicio",
    "neighbor_km_fin",
    "distance_order",
    "weight",
    "fuente",
]


class SegmentGraphContractError(ValueError):
    """Indica que una entrada o salida viola el contrato del grafo V2."""


def _whole_km(value: str, column: str, row_number: int) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise SegmentGraphContractError(
            f"Fila {row_number}: {column} no es numerico: {value!r}."
        ) from exc

    if not number.is_integer():
        raise SegmentGraphContractError(
            f"Fila {row_number}: {column} debe ser entero, recibido {value!r}."
        )
    return int(number)


def segment_id(km_inicio: int, km_fin: int) -> str:
    """Devuelve la identidad V2 determinista de un segmento de 1 km."""

    if km_inicio < 0 or km_fin != km_inicio + 1:
        raise SegmentGraphContractError(
            f"Limites invalidos para segment_id: ({km_inicio}, {km_fin})."
        )
    return f"seg_{km_inicio:03d}_{km_fin:03d}"


def load_segment_keys(path: Path = DEFAULT_SOURCE) -> list[tuple[int, int]]:
    """Carga y valida las claves longitudinales canónicas de V1."""

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        required = {"km_inicio", "km_fin"}
        if not required.issubset(columns):
            missing = ", ".join(sorted(required - columns))
            raise SegmentGraphContractError(f"Faltan columnas V1: {missing}.")

        keys = [
            (
                _whole_km(row["km_inicio"], "km_inicio", row_number),
                _whole_km(row["km_fin"], "km_fin", row_number),
            )
            for row_number, row in enumerate(reader, start=2)
        ]

    if keys != EXPECTED_KEYS:
        raise SegmentGraphContractError(
            "segmentos.csv debe contener exactamente las 130 claves ordenadas "
            "desde (0, 1) hasta (129, 130)."
        )
    return keys


def build_neighbor_rows(
    keys: Sequence[tuple[int, int]],
) -> list[dict[str, object]]:
    """Construye una lista dirigida de vecinos contiguos de primer orden."""

    if list(keys) != EXPECTED_KEYS:
        raise SegmentGraphContractError(
            "El grafo V2 solo se genera para la cobertura canónica km 0-130."
        )

    rows: list[dict[str, object]] = []
    for index, (km_inicio, km_fin) in enumerate(keys):
        neighbor_indexes = [candidate for candidate in (index - 1, index + 1) if 0 <= candidate < len(keys)]
        for neighbor_index in neighbor_indexes:
            neighbor_inicio, neighbor_fin = keys[neighbor_index]
            rows.append(
                {
                    "segment_id": segment_id(km_inicio, km_fin),
                    "km_inicio": km_inicio,
                    "km_fin": km_fin,
                    "neighbor_segment_id": segment_id(neighbor_inicio, neighbor_fin),
                    "neighbor_km_inicio": neighbor_inicio,
                    "neighbor_km_fin": neighbor_fin,
                    "distance_order": 1,
                    "weight": "1.0",
                    "fuente": "derived:v1_segment_order",
                }
            )

    validate_neighbor_rows(rows, keys)
    return rows


def validate_neighbor_rows(
    rows: Sequence[dict[str, object]],
    keys: Sequence[tuple[int, int]],
) -> None:
    """Aplica invariantes estructurales antes de publicar el grafo."""

    if len(rows) != 258:
        raise SegmentGraphContractError(
            f"Se esperaban 258 aristas dirigidas; se obtuvieron {len(rows)}."
        )

    edges: set[tuple[str, str]] = set()
    degree = {segment_id(*key): 0 for key in keys}
    for row in rows:
        origin = str(row["segment_id"])
        neighbor = str(row["neighbor_segment_id"])
        edge = (origin, neighbor)
        if origin == neighbor:
            raise SegmentGraphContractError(f"Autoarista no permitida: {origin}.")
        if edge in edges:
            raise SegmentGraphContractError(f"Arista duplicada: {edge}.")
        edges.add(edge)
        degree[origin] += 1

        origin_km = int(row["km_inicio"])
        neighbor_km = int(row["neighbor_km_inicio"])
        if abs(origin_km - neighbor_km) != 1:
            raise SegmentGraphContractError(f"Vecindad no contigua: {edge}.")

    missing_reciprocals = [edge for edge in edges if (edge[1], edge[0]) not in edges]
    if missing_reciprocals:
        raise SegmentGraphContractError(
            f"Aristas sin reciproca: {missing_reciprocals[:3]}."
        )

    expected_degree = {
        segment_id(*key): 1 if index in (0, len(keys) - 1) else 2
        for index, key in enumerate(keys)
    }
    if degree != expected_degree:
        raise SegmentGraphContractError("El grado de los nodos no describe una cadena lineal.")


def render_csv(rows: Iterable[dict[str, object]]) -> str:
    """Serializa el producto con orden y saltos de linea deterministas."""

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def write_atomic(path: Path, content: str) -> None:
    """Publica el CSV sin dejar un archivo parcial ante una interrupcion."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(content)
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def generate(source: Path = DEFAULT_SOURCE) -> str:
    """Genera en memoria el CSV canónico del grafo."""

    keys = load_segment_keys(source)
    return render_csv(build_neighbor_rows(keys))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Comprueba que el producto versionado coincide con la regeneración.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    expected = generate(args.source)

    if args.check:
        if not args.output.exists():
            raise SystemExit(f"ERROR: no existe el producto esperado: {args.output}")
        observed = args.output.read_text(encoding="utf-8")
        if observed != expected:
            raise SystemExit(
                "ERROR: segment_neighbors.csv no coincide con su regeneración determinista."
            )
        print(f"OK: {args.output} coincide con la regeneración (258 aristas).")
        return 0

    write_atomic(args.output, expected)
    print(f"OK: {args.output} generado con 130 nodos y 258 aristas dirigidas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
