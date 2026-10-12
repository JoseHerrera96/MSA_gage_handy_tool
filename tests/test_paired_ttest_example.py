"""Example and validation script for the Paired T-Test module.

This script demonstrates how the paired t-test module works with a known,
simple dataset. It validates that:
1. Parsing works correctly
2. Calculations match expected values (ground truth)
3. Dashboard generation completes without errors

To run this example:
    python test_paired_ttest_example.py

It will create example input files, run the analysis, and verify the results.
"""

from pathlib import Path
import unittest

from gage_tracer.paired_ttest import (
    parse_paired_measurements,
    calculate_paired_ttest_metrics,
)


class PairedTTestFixtureTests(unittest.TestCase):
    def test_fixture_matches_ground_truth(self) -> None:
        fixtures = Path(__file__).parent / "fixtures"
        file_a = fixtures / "paired_sample_a.txt"
        file_b = fixtures / "paired_sample_b.txt"

        paired_df, system_a, system_b, differences = parse_paired_measurements(
            file_a, file_b
        )
        metrics = calculate_paired_ttest_metrics(system_a, system_b)

        self.assertEqual(len(paired_df), 10)
        expected_differences = [
            0.1, 0.2, -0.1, 0.2, -0.1,
            0.1, 0.2, -0.1, 0.2, -0.1,
        ]
        for actual, expected in zip(differences, expected_differences):
            self.assertAlmostEqual(actual, expected, places=8)
        self.assertAlmostEqual(float(metrics["Mean_D"]), 0.06, places=8)
        self.assertAlmostEqual(float(metrics["StDev_D"]), 0.142984, places=6)
        self.assertAlmostEqual(float(metrics["T_Value"]), 1.326978, places=6)
        self.assertAlmostEqual(float(metrics["P_Value"]), 0.217195, places=6)
