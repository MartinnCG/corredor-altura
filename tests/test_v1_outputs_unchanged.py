"""Protege byte a byte los cuatro productos canónicos publicados en V1."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHA256 = {
    "data/processed/segmentos.csv": "fcfe2c5ba1b04f9f7de217f7644aa629573813be8a31da384dd104d11ef97cb2",
    "data/processed/features_segmentos_master.csv": "773573767e0352c9c6650d4fe14564b786b3cb8cef6ff4bf90f9cef26763b93e",
    "data/processed/indice_exposicion_segmentos.csv": "ed419b327081d901140554837349c77cf84770de78379032d5987715d925d4dc",
    "data/processed/validacion_indice_exposicion.csv": "ced34ac9b87fe03de889a0f01cccebad8c408311e9cfef20ac6dc6fc1affdb26",
}


class V1OutputsUnchangedTests(unittest.TestCase):
    def test_canonical_v1_files_match_release_hashes(self) -> None:
        for relative_path, expected_hash in EXPECTED_SHA256.items():
            with self.subTest(path=relative_path):
                observed_hash = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
                self.assertEqual(observed_hash, expected_hash)


if __name__ == "__main__":
    unittest.main()
