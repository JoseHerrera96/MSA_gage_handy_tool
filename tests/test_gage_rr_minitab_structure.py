import unittest
from pathlib import Path

import pandas as pd

from gage_tracer.calculations import calculate_gage_rr_crossed


class GageRRCalculationTests(unittest.TestCase):
    def test_variance_components_include_operator_row_from_fixture(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "gage_rr_sample.txt"
        df = pd.read_csv(fixture, sep="\t")
        result = calculate_gage_rr_crossed(df, tolerance=10.0)
        sources = result["variance_components"]["Source"].tolist()

        self.assertIn("Operator", sources)
        self.assertIn("Repeatability", sources)
        self.assertIn("Reproducibility", sources)
        self.assertIn("Part-to-Part", sources)
        self.assertIn("Total Variation", sources)
