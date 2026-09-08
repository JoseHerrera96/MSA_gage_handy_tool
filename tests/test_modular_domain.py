"""Focused regression tests for shared MSA domain rules."""

from __future__ import annotations

import sys
import unittest
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gage_tracer.data_parser import transform_gage_rr_data
from gage_tracer.study_config import GRR_DESIGN, classify_gage_rr


def _measurement_row(tag: str, value: float = 1.0) -> str:
    return f'"{tag}"\t{value:.4f}\t1.0000\t0.1000\t-0.1000'


class StudyConfigTests(unittest.TestCase):
    def test_fixed_crossed_design(self) -> None:
        self.assertEqual(GRR_DESIGN.report_blocks, 90)
        self.assertEqual(GRR_DESIGN.parts, 10)
        self.assertEqual(GRR_DESIGN.operators, 3)
        self.assertEqual(GRR_DESIGN.trials_per_part, 3)

    def test_gage_rr_verdict_policy(self) -> None:
        self.assertEqual(classify_gage_rr(9.99, 5), "PASS")
        self.assertEqual(classify_gage_rr(10.0, 5), "MARGINAL")
        self.assertEqual(classify_gage_rr(31.0, 5), "FAIL")
        self.assertEqual(classify_gage_rr(5.0, 4), "FAIL")


class GageRRParserTests(unittest.TestCase):
    def test_part_tagged_single_dimension_layout(self) -> None:
        rows = []
        for round_number in range(9):
            for part_number in range(1, 11):
                rows.append(_measurement_row(f"C20_A{part_number:03d}", round_number + part_number / 100))

        data = ":BEGIN\n" + "\n".join(rows) + "\nEND\n"
        frame = transform_gage_rr_data(StringIO(data))

        self.assertEqual(len(frame), 90)
        self.assertEqual(frame["Report"].nunique(), 90)
        self.assertEqual(frame["Part"].nunique(), 10)
        self.assertEqual(frame["Operator"].nunique(), 3)
        self.assertEqual(frame["Trial"].nunique(), 3)
        self.assertEqual(frame["Characteristic"].unique().tolist(), ["C20"])


if __name__ == "__main__":
    unittest.main()
