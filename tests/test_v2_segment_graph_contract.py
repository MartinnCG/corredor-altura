"""Pruebas contractuales del grafo lineal de segmentos V2."""

from __future__ import annotations

import csv
import io
import unittest
from collections import Counter, deque
from pathlib import Path

from src.segment.generar_grafo_segmentos_v2 import (
    DEFAULT_OUTPUT,
    EXPECTED_KEYS,
    FIELDNAMES,
    build_neighbor_rows,
    generate,
    load_segment_keys,
    segment_id,
)


class V2SegmentGraphContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.keys = load_segment_keys()
        cls.rows = build_neighbor_rows(cls.keys)

    def test_segment_identity_is_complete_stable_and_ordered(self) -> None:
        self.assertEqual(self.keys, EXPECTED_KEYS)
        identities = [segment_id(*key) for key in self.keys]
        self.assertEqual(len(identities), 130)
        self.assertEqual(len(set(identities)), 130)
        self.assertEqual(identities[0], "seg_000_001")
        self.assertEqual(identities[-1], "seg_129_130")

    def test_graph_has_expected_directed_edges_and_degrees(self) -> None:
        self.assertEqual(len(self.rows), 258)
        edges = {
            (str(row["segment_id"]), str(row["neighbor_segment_id"]))
            for row in self.rows
        }
        self.assertEqual(len(edges), 258)
        self.assertTrue(all(origin != neighbor for origin, neighbor in edges))
        self.assertTrue(all((neighbor, origin) in edges for origin, neighbor in edges))

        degrees = Counter(origin for origin, _ in edges)
        self.assertEqual(degrees["seg_000_001"], 1)
        self.assertEqual(degrees["seg_129_130"], 1)
        for km in range(1, 129):
            self.assertEqual(degrees[segment_id(km, km + 1)], 2)

    def test_edges_connect_only_consecutive_segments(self) -> None:
        for row in self.rows:
            with self.subTest(edge=(row["segment_id"], row["neighbor_segment_id"])):
                self.assertEqual(
                    abs(int(row["km_inicio"]) - int(row["neighbor_km_inicio"])),
                    1,
                )
                self.assertEqual(row["distance_order"], 1)
                self.assertEqual(row["weight"], "1.0")
                self.assertEqual(row["fuente"], "derived:v1_segment_order")

    def test_graph_is_connected(self) -> None:
        adjacency: dict[str, set[str]] = {}
        for row in self.rows:
            adjacency.setdefault(str(row["segment_id"]), set()).add(
                str(row["neighbor_segment_id"])
            )

        visited: set[str] = set()
        pending = deque(["seg_000_001"])
        while pending:
            node = pending.popleft()
            if node in visited:
                continue
            visited.add(node)
            pending.extend(adjacency[node] - visited)

        self.assertEqual(visited, set(adjacency))
        self.assertEqual(len(visited), 130)

    def test_versioned_product_matches_deterministic_regeneration(self) -> None:
        observed = DEFAULT_OUTPUT.read_text(encoding="utf-8")
        expected = generate()
        self.assertEqual(observed, expected)

        reader = csv.DictReader(io.StringIO(observed))
        self.assertEqual(list(reader.fieldnames or []), FIELDNAMES)
        self.assertEqual(len(list(reader)), 258)


if __name__ == "__main__":
    unittest.main()
