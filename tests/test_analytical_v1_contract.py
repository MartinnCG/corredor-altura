"""Release-gate tests for Corredor de Altura analytical v1.

These checks validate published data contracts. They deliberately do not
recalculate the exposure model or require geospatial system dependencies.
"""

from __future__ import annotations

import csv
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
EXPECTED_KEYS = {(km, km + 1) for km in range(130)}

DATASETS = {
    "segments": PROCESSED / "segmentos.csv",
    "master": PROCESSED / "features_segmentos_master.csv",
    "exposure": PROCESSED / "indice_exposicion_segmentos.csv",
    "validation": PROCESSED / "validacion_indice_exposicion.csv",
}

REQUIRED_MASTER_COLUMNS = {
    "km_inicio",
    "km_fin",
    "pendiente_media_abs_pct",
    "pendiente_terreno_p90_pct",
    "n_drenajes_principales_50m",
    "area_aportante_max_50m_km2",
    "precipitacion_diaria_p95_mm",
    "viento_p95_ms",
    "fraccion_horas_nieve_ge50pct",
}

EXPOSURE_CLASSES = {"muy_baja", "baja", "media", "alta", "muy_alta"}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def segment_key(row: dict[str, str]) -> tuple[int, int]:
    return int(row["km_inicio"]), int(row["km_fin"])


class AnalyticalV1ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.loaded = {name: read_csv(path) for name, path in DATASETS.items()}

    def test_canonical_datasets_cover_exactly_km_0_130(self) -> None:
        for name, (_, rows) in self.loaded.items():
            with self.subTest(dataset=name):
                self.assertEqual(len(rows), 130)
                keys = [segment_key(row) for row in rows]
                self.assertEqual(len(keys), len(set(keys)), "duplicate segment key")
                self.assertEqual(set(keys), EXPECTED_KEYS)
                self.assertEqual(keys, sorted(keys), "segments are not ordered")

    def test_master_schema_and_completeness(self) -> None:
        columns, rows = self.loaded["master"]
        self.assertEqual(len(columns), 46)
        self.assertTrue(REQUIRED_MASTER_COLUMNS.issubset(columns))
        blanks = [
            (row_number, column)
            for row_number, row in enumerate(rows, start=2)
            for column, value in row.items()
            if value is None or not value.strip()
        ]
        self.assertEqual(blanks, [], f"blank master values: {blanks[:10]}")

    def test_exposure_outputs_respect_published_domain(self) -> None:
        _, rows = self.loaded["exposure"]
        rankings = {int(row["ranking_exposicion"]) for row in rows}
        self.assertEqual(rankings, set(range(1, 131)))

        for row in rows:
            score = float(row["indice_exposicion"])
            self.assertTrue(math.isfinite(score))
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 100.0)
            self.assertIn(row["clase_exposicion"], EXPOSURE_CLASSES)

    def test_validation_preserves_model_outputs(self) -> None:
        _, exposure_rows = self.loaded["exposure"]
        _, validation_rows = self.loaded["validation"]
        exposure = {segment_key(row): row for row in exposure_rows}
        validation = {segment_key(row): row for row in validation_rows}

        self.assertEqual(exposure.keys(), validation.keys())
        for key, expected in exposure.items():
            observed = validation[key]
            with self.subTest(segment=key):
                self.assertEqual(
                    int(observed["ranking_exposicion"]),
                    int(expected["ranking_exposicion"]),
                )
                self.assertEqual(
                    observed["clase_exposicion"],
                    expected["clase_exposicion"],
                )
                self.assertAlmostEqual(
                    float(observed["indice_exposicion"]),
                    float(expected["indice_exposicion"]),
                    places=9,
                )


if __name__ == "__main__":
    unittest.main()
