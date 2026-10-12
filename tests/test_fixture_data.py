import math
from pathlib import Path
import unittest

import pandas as pd

from gage_tracer.calculations import calculate_type1_metrics


class SyntheticFixtureTests(unittest.TestCase):
    def test_type1_fixture_produces_metrics(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "type1_sample_data.txt"
        frame = pd.read_csv(fixture, sep="\t")
        row = frame.loc[frame["Dimension"] == "C5"].iloc[0]
        measurement_columns = frame.columns[4:]
        measurements = pd.to_numeric(row[measurement_columns])

        result = calculate_type1_metrics("C5", measurements, row)

        self.assertEqual(result["Observations"], len(measurement_columns))
        self.assertEqual(result["Gage Item"], "C5")
        self.assertTrue(math.isfinite(float(result["Cg"])))
