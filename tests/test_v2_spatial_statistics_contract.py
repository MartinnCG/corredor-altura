"""Pruebas contractuales de estadistica espacial V2."""

from __future__ import annotations

import json
import unittest
from collections import Counter

from src.features.calcular_estadistica_espacial_v2 import (
    DEFAULT_LOCAL_OUTPUT,
    DEFAULT_SUMMARY_OUTPUT,
    analyze,
    generate,
    load_config,
    load_neighbors,
)


class V2SpatialStatisticsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config()
        cls.rows, cls.summary = analyze(cls.config)

    def test_analysis_is_explicitly_simulated(self) -> None:
        self.assertIs(self.config["simulation_only"], True)
        self.assertIs(self.config["operational_use_allowed"], False)
        self.assertIs(self.summary["simulation_only"], True)
        self.assertIs(self.summary["operational_use_allowed"], False)
        self.assertTrue(all(row["is_simulated"] == "true" for row in self.rows))
        self.assertTrue(all(str(row["fuente"]).startswith("simulation:") for row in self.rows))

    def test_weights_are_complete_reciprocal_and_without_islands(self) -> None:
        ids, neighbors = load_neighbors()
        self.assertEqual(len(ids), 130)
        self.assertEqual(sum(len(value) for value in neighbors.values()), 258)
        self.assertTrue(all(neighbors[identity] for identity in ids))
        for origin, adjacent in neighbors.items():
            for neighbor in adjacent:
                self.assertIn(origin, neighbors[neighbor])

    def test_global_statistics_use_permutation_inference(self) -> None:
        for label in ("primary", "sensitivity"):
            result = self.summary[label]
            self.assertEqual(result["permutations"], 9999)
            self.assertGreaterEqual(result["moran_p_sim"], 0.0001)
            self.assertLessEqual(result["moran_p_sim"], 1.0)
            self.assertGreaterEqual(result["geary_p_sim"], 0.0001)
            self.assertLessEqual(result["geary_p_sim"], 1.0)
        self.assertEqual(self.summary["primary"]["transformation"], "r")
        self.assertEqual(self.summary["sensitivity"]["transformation"], "b")

    def test_local_results_apply_fdr_and_preserve_order(self) -> None:
        self.assertEqual(len(self.rows), 130)
        self.assertEqual(
            self.summary["local_inference"]["alternative"], "two-sided"
        )
        self.assertEqual(self.rows[0]["segment_id"], "seg_000_001")
        self.assertEqual(self.rows[-1]["segment_id"], "seg_129_130")
        for row in self.rows:
            with self.subTest(segment=row["segment_id"]):
                self.assertGreaterEqual(float(row["p_fdr_bh"]), float(row["p_sim"]))
                significant = row["significant_fdr"] == "true"
                self.assertEqual(
                    significant,
                    row["lisa_cluster_fdr"] != "not_significant",
                )

    def test_summary_counts_match_local_rows(self) -> None:
        observed = Counter(str(row["lisa_cluster_fdr"]) for row in self.rows)
        expected = {
            key: value
            for key, value in self.summary["local_inference"][
                "cluster_counts_fdr"
            ].items()
            if value
        }
        self.assertEqual(observed, expected)
        self.assertEqual(
            self.summary["local_inference"]["significant_fdr"],
            sum(row["significant_fdr"] == "true" for row in self.rows),
        )

    def test_software_versions_are_recorded(self) -> None:
        self.assertEqual(self.summary["software"]["esda"], "2.10.0")
        self.assertEqual(self.summary["software"]["libpysal"], "4.15.0")
        self.assertIn("numpy", self.summary["software"])
        self.assertIn("scipy", self.summary["software"])

    def test_versioned_products_match_regeneration(self) -> None:
        local_csv, summary_json = generate()
        self.assertEqual(DEFAULT_LOCAL_OUTPUT.read_text(encoding="utf-8"), local_csv)
        self.assertEqual(
            DEFAULT_SUMMARY_OUTPUT.read_text(encoding="utf-8"), summary_json
        )
        parsed = json.loads(summary_json)
        self.assertEqual(parsed["n_segments"], 130)


if __name__ == "__main__":
    unittest.main()
