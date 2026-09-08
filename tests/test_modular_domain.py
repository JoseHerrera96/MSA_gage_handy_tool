"""Focused regression tests for shared MSA domain rules."""

from __future__ import annotations

import sys
import unittest
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from gage_tracer.data_parser import transform_gage_rr_data
from gage_tracer.paired_ttest import (
    calculate_paired_ttest_diagnostics,
    calculate_paired_ttest_metrics,
    create_paired_ttest_dashboard,
)
from gage_tracer.presentation import (
    format_paired_preview,
    paired_data_quality_summary,
    paired_descriptive_dataframe,
)
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


class PairedPresentationTests(unittest.TestCase):
    def test_paired_preview_formats_columns(self) -> None:
        paired_df = pd.DataFrame(
            {
                "Observation": [1, 2],
                "System_A": [10.1, 10.2],
                "System_B": [10.0, 10.1],
                "Difference": [0.1, 0.1],
            }
        )
        preview = format_paired_preview(paired_df)

        self.assertEqual(preview.columns.tolist(), ["Obs", "System A", "System B", "A − B"])
        self.assertEqual(preview.loc[0, "A − B"], "+0.100000")

    def test_paired_quality_summary(self) -> None:
        paired_df = pd.DataFrame(
            {
                "Observation": [1, 2],
                "System_A": [10.1, 10.2],
                "System_B": [10.0, 10.1],
                "Difference": [0.1, 0.1],
            }
        )
        summary = paired_data_quality_summary(paired_df)

        self.assertEqual(summary.loc["Paired observations", "Value"], "2")
        self.assertEqual(summary.loc["Difference range", "Value"], "+0.100000 to +0.100000")
        self.assertEqual(summary.loc["Zero differences", "Value"], "0")

    def test_paired_descriptive_summary(self) -> None:
        metrics = {
            "N": 2,
            "Mean_A": 10.15,
            "Mean_B": 10.05,
            "Mean_D": 0.10,
            "StDev_A": 0.07,
            "StDev_B": 0.07,
            "StDev_D": 0.0,
            "SE_A": 0.05,
            "SE_B": 0.05,
            "SE_D": 0.0,
        }
        summary = paired_descriptive_dataframe(metrics)

        self.assertEqual(summary["Variable"].tolist(), ["System A", "System B", "Difference (A − B)"])
        self.assertEqual(summary.loc[2, "Mean"], "0.100000")


class PairedDiagnosticTests(unittest.TestCase):
    def test_detects_severe_difference_outlier(self) -> None:
        system_a = [10.0] * 10 + [20.0]
        system_b = [10.0] * 11
        diagnostics = calculate_paired_ttest_diagnostics(system_a, system_b)

        self.assertEqual(diagnostics["Outlier_Positions"], [11])
        self.assertEqual(diagnostics["Outlier_Status"], "WARNING")

    def test_large_sample_marks_normality_and_size_as_pass(self) -> None:
        system_a = [float(index) for index in range(20)]
        system_b = [float(index) - 0.1 for index in range(20)]
        diagnostics = calculate_paired_ttest_diagnostics(system_a, system_b)

        self.assertEqual(diagnostics["Normality_Status"], "PASS")
        self.assertEqual(diagnostics["Sample_Size_Status"], "PASS")
        self.assertGreater(diagnostics["Detectable_Differences"][0.90], 0)

    def test_html_report_contains_all_preview_sections_and_charts(self) -> None:
        paired_df = pd.DataFrame(
            {
                "Observation": [1, 2, 3, 4, 5],
                "System_A": [10.1, 10.3, 10.2, 10.4, 10.0],
                "System_B": [10.0, 10.1, 10.3, 10.2, 10.1],
            }
        )
        paired_df["Difference"] = paired_df["System_A"] - paired_df["System_B"]
        metrics = calculate_paired_ttest_metrics(
            paired_df["System_A"].tolist(), paired_df["System_B"].tolist()
        )
        report_html = create_paired_ttest_dashboard(paired_df, metrics)

        for section in ("Summary Report", "Diagnostic Report", "Report Card"):
            self.assertIn(section, report_html)
        self.assertIn("Paired data in worksheet order", report_html)
        self.assertIn("Power and detectable difference analysis", report_html)
        self.assertEqual(report_html.count("data:image/png;base64,"), 7)


if __name__ == "__main__":
    unittest.main()
