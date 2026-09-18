"""Pruebas contractuales del change-control simulado de V2."""

from __future__ import annotations

import csv
import io
import unittest
from collections import Counter

from src.features.generar_change_control_demo_v2 import (
    DEFAULT_EVENTS,
    DEFAULT_SNAPSHOTS,
    EVENT_FIELDS,
    SNAPSHOT_FIELDS,
    build_demo,
    generate,
    load_config,
)


class V2ChangeControlDemoContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config()
        cls.snapshots, cls.events = build_demo(cls.config)

    def test_config_forbids_operational_use(self) -> None:
        self.assertIs(self.config["simulation_only"], True)
        self.assertIs(self.config["operational_use_allowed"], False)
        self.assertTrue(self.config["scenario_id"].startswith("demo_"))
        self.assertTrue(self.config["provenance"]["fuente"].startswith("simulation:"))

    def test_complete_temporal_coverage(self) -> None:
        self.assertEqual(len(self.snapshots), 260)
        self.assertEqual(len(self.events), 130)
        counts = Counter(str(row["segment_id"]) for row in self.snapshots)
        self.assertEqual(len(counts), 130)
        self.assertEqual(set(counts.values()), {2})
        self.assertEqual(len({row["change_event_id"] for row in self.events}), 130)

    def test_simulation_is_marked_on_every_row(self) -> None:
        scenario_id = self.config["scenario_id"]
        for row in self.snapshots + self.events:
            with self.subTest(segment=row["segment_id"]):
                self.assertEqual(row["is_simulated"], "true")
                self.assertEqual(row["simulation_scenario_id"], scenario_id)
                self.assertTrue(str(row["fuente"]).startswith("simulation:"))

        self.assertTrue(
            all(row["evidence_type"] == "simulated" for row in self.snapshots)
        )
        self.assertTrue(all(float(row["confidence"]) == 0.0 for row in self.events))

    def test_event_values_are_recomputed_from_snapshots(self) -> None:
        by_key = {
            (str(row["segment_id"]), str(row["observed_at_utc"])): row
            for row in self.snapshots
        }
        for event in self.events:
            baseline = by_key[
                (str(event["segment_id"]), str(event["baseline_snapshot_at_utc"]))
            ]
            current = by_key[
                (str(event["segment_id"]), str(event["current_snapshot_at_utc"]))
            ]
            expected_delta = float(current["metric_value"]) - float(
                baseline["metric_value"]
            )
            with self.subTest(segment=event["segment_id"]):
                self.assertAlmostEqual(float(event["delta_abs"]), expected_delta)
                self.assertAlmostEqual(
                    float(event["delta_pct"]),
                    expected_delta / float(baseline["metric_value"]) * 100.0,
                    places=5,
                )

    def test_uncertainty_contains_each_simulated_value(self) -> None:
        for row in self.snapshots:
            value = float(row["metric_value"])
            with self.subTest(segment=row["segment_id"], at=row["observed_at_utc"]):
                self.assertLessEqual(float(row["uncertainty_lower"]), value)
                self.assertGreaterEqual(float(row["uncertainty_upper"]), value)

    def test_change_classes_match_configured_demo_zones(self) -> None:
        classes = Counter(str(row["change_class"]) for row in self.events)
        self.assertEqual(classes, {"stable": 105, "major": 10, "moderate": 15})

    def test_versioned_products_match_deterministic_regeneration(self) -> None:
        expected_snapshots, expected_events = generate()
        self.assertEqual(
            DEFAULT_SNAPSHOTS.read_text(encoding="utf-8"), expected_snapshots
        )
        self.assertEqual(DEFAULT_EVENTS.read_text(encoding="utf-8"), expected_events)

        snapshot_reader = csv.DictReader(io.StringIO(expected_snapshots))
        event_reader = csv.DictReader(io.StringIO(expected_events))
        self.assertEqual(list(snapshot_reader.fieldnames or []), SNAPSHOT_FIELDS)
        self.assertEqual(list(event_reader.fieldnames or []), EVENT_FIELDS)


if __name__ == "__main__":
    unittest.main()
