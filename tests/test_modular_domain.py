"""Focused regression tests for shared MSA domain rules."""

from __future__ import annotations

import sys
import unittest
import zipfile
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from gage_tracer.data_parser import (
    paired_input_has_blocks,
    transform_gage_rr_data,
    transform_paired_multicharacteristic_data,
)
from gage_tracer.calculations import calculate_gage_rr_by_characteristic
from gage_tracer.paired_ttest import (
    build_paired_ttest_overview_dataframe,
    calculate_paired_ttest_diagnostics,
    calculate_paired_ttest_metrics,
    create_paired_ttest_dashboard,
    create_paired_ttest_html_overview,
    create_paired_ttest_html_zip,
    parse_paired_measurements,
    parse_paired_multicharacteristic_measurements,
)
from gage_tracer.presentation import (
    format_paired_preview,
    paired_data_quality_summary,
    paired_descriptive_dataframe,
)
from gage_tracer.study_config import GRR_DESIGN, classify_gage_rr
from gage_tracer.visualization import (
    build_gage_rr_overview_dataframe,
    create_gage_rr_html_overview,
    create_gage_rr_html_zip,
)


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
    def test_untagged_reports_use_part_operator_trial_order_by_default(self) -> None:
        data = "\n".join(
            f":BEGIN\n{_measurement_row('C20_A001', report_number)}\n:END"
            for report_number in range(GRR_DESIGN.report_blocks)
        )
        frame = transform_gage_rr_data(StringIO(data))

        expected = {
            1: ("Part_1", "Operator_1", 1),
            3: ("Part_1", "Operator_1", 3),
            4: ("Part_1", "Operator_2", 1),
            10: ("Part_2", "Operator_1", 1),
            90: ("Part_10", "Operator_3", 3),
        }
        for report, factors in expected.items():
            row = frame.loc[frame["Report"] == report].iloc[0]
            self.assertEqual((row["Part"], row["Operator"], row["Trial"]), factors)

    def test_untagged_reports_can_use_operator_major_order(self) -> None:
        data = "\n".join(
            f":BEGIN\n{_measurement_row('C20_A001', report_number)}\n:END"
            for report_number in range(GRR_DESIGN.report_blocks)
        )
        frame = transform_gage_rr_data(StringIO(data), report_order="operator-major")

        expected = {
            1: ("Part_1", "Operator_1", 1),
            4: ("Part_2", "Operator_1", 1),
            31: ("Part_1", "Operator_2", 1),
            90: ("Part_10", "Operator_3", 3),
        }
        for report, factors in expected.items():
            row = frame.loc[frame["Report"] == report].iloc[0]
            self.assertEqual((row["Part"], row["Operator"], row["Trial"]), factors)

    def test_parser_recovers_joined_and_control_prefixed_markers(self) -> None:
        data = "\n".join(
            f'":BEGIN"\n{_measurement_row("C20_A001", report_number)}\n":END"'
            for report_number in range(GRR_DESIGN.report_blocks)
        )
        data = data.replace('":END"\n":BEGIN"', '":END"":BEGIN"', 1)
        data = data.replace('":END"\n":BEGIN"', '":END"\n\x1a":BEGIN"', 1)

        frame = transform_gage_rr_data(StringIO(data))

        self.assertEqual(frame["Report"].nunique(), GRR_DESIGN.report_blocks)
        self.assertEqual(len(frame), GRR_DESIGN.report_blocks)

    def test_html_reports_are_zipped_with_safe_unique_names(self) -> None:
        data = "\n".join(
            f"BEGIN\n{_measurement_row('C20/A001', report_number)}\n"
            f"{_measurement_row('C20_A001', report_number)}\nEND"
            for report_number in range(GRR_DESIGN.report_blocks)
        )
        frame = transform_gage_rr_data(StringIO(data))
        results = calculate_gage_rr_by_characteristic(frame)
        overview = build_gage_rr_overview_dataframe(results)

        with patch(
            "gage_tracer.visualization.create_gage_rr_html_dashboard",
            side_effect=lambda report_df, _: f"<html>{report_df['Characteristic'].iloc[0]}</html>",
        ):
            overview_html = create_gage_rr_html_overview(frame, results)
            archive_bytes = create_gage_rr_html_zip(frame, results)

        self.assertEqual(overview.iloc[0]["Total Gage R&R (% Study Var)"], overview["Total Gage R&R (% Study Var)"].max())
        self.assertIn("Results by Characteristic", overview_html)
        self.assertIn("C20/A001", overview_html)
        with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
            names = archive.namelist()
            self.assertEqual(len(names), 3)
            self.assertEqual(names[0], "000_Gage_RR_Study_Overview.html")
            self.assertNotEqual(names[1], names[2])
            self.assertEqual(
                [archive.read(name).decode("utf-8") for name in names[1:]],
                ["<html>C20/A001</html>", "<html>C20_A001</html>"],
            )
            self.assertIn("Gage R&amp;R Study Overview", archive.read(names[0]).decode("utf-8"))

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


class PairedBlockParserTests(unittest.TestCase):
    def test_legacy_numeric_parser_rejects_text_and_nonfinite_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "System A line 2 is not a numeric"):
            parse_paired_measurements(StringIO("1.0\nheader\n2.0"), StringIO("1.0\n2.0"))
        with self.assertRaisesRegex(ValueError, "System B line 2 must contain a finite"):
            parse_paired_measurements(StringIO("1.0\n2.0"), StringIO("1.0\nnan"))

    def test_parses_consistent_characteristics_from_report_blocks(self) -> None:
        data = "\n".join(
            '":BEGIN"\n'
            + "\n".join(
                f'"C{characteristic}"\t{report + characteristic / 10}\t1\t1\t-1'
                for characteristic in (1, 2)
            )
            + '\n":END"'
            for report in range(1, 4)
        )
        frame = transform_paired_multicharacteristic_data(StringIO(data))

        self.assertEqual(frame["Observation"].nunique(), 3)
        self.assertEqual(frame["Characteristic"].unique().tolist(), ["C1", "C2"])
        self.assertEqual(frame.groupby("Characteristic").size().to_dict(), {"C1": 3, "C2": 3})

    def test_rejects_changed_characteristic_set_and_bad_measurements(self) -> None:
        changed_set = (
            ':BEGIN\n"C1"\t1\t1\t1\t-1\n:END\n'
            ':BEGIN\n"C2"\t2\t1\t1\t-1\n:END'
        )
        malformed = ':BEGIN\n"C1"\tnot-a-number\t1\t1\t-1\n:END'

        with self.assertRaisesRegex(ValueError, "different set of characteristics"):
            transform_paired_multicharacteristic_data(StringIO(changed_set))
        with self.assertRaisesRegex(ValueError, "invalid measurement"):
            transform_paired_multicharacteristic_data(StringIO(malformed))

    def test_repairs_joined_and_control_prefixed_markers(self) -> None:
        data = "\n".join(
            f'":BEGIN"\n"C1"\t{value}\t1\t1\t-1\n"C2"\t{value + 1}\t1\t1\t-1\n":END"'
            for value in range(1, 4)
        )
        data = data.replace('":END"\n":BEGIN"', '":END"":BEGIN"', 1)
        data = data.replace('":END"\n":BEGIN"', '":END"\n\x1a":BEGIN"', 1)

        frame = transform_paired_multicharacteristic_data(StringIO(data))
        self.assertEqual(frame["Observation"].nunique(), 3)
        self.assertEqual(len(frame), 6)

    def test_accepts_grr_metadata_and_optional_trailing_columns(self) -> None:
        data = "\n".join(
            f':BEGIN\t"time"\n"PATTERN: study"\n"DISPLAY: sample"\n"UNIT: mm"\n'
            f'"C1"\t{value}\t10\t1\t-1\t0\t0\n'
            f'"C2"\t{value + 1}\t10\t1\t-1\t0\t0\n:END'
            for value in (1, 2)
        )
        frame = transform_paired_multicharacteristic_data(StringIO(data))
        self.assertEqual(len(frame), 4)
        self.assertEqual(frame["Measurement"].tolist(), [1.0, 2.0, 2.0, 3.0])

    def test_rejects_unrecognized_rows_nonfinite_values_and_prefix_markers(self) -> None:
        malformed_row = ':BEGIN\nC1 measurement\n:END'
        nonfinite = ':BEGIN\n"C1"\tnan\n:END'
        prefix_marker = ':BEGINNING'
        outside_block = '"C1"\t1\n:BEGIN\n"C1"\t1\n:END'

        with self.assertRaisesRegex(ValueError, "tab-separated"):
            transform_paired_multicharacteristic_data(StringIO(malformed_row))
        with self.assertRaisesRegex(ValueError, "must be finite"):
            transform_paired_multicharacteristic_data(StringIO(nonfinite))
        self.assertFalse(paired_input_has_blocks(StringIO(prefix_marker)))
        with self.assertRaisesRegex(ValueError, "not inside a BEGIN/END"):
            transform_paired_multicharacteristic_data(StringIO(prefix_marker))
        with self.assertRaisesRegex(ValueError, "not inside a BEGIN/END"):
            transform_paired_multicharacteristic_data(StringIO(outside_block))

    def test_aligns_systems_and_rejects_different_block_counts(self) -> None:
        def report_blocks(characteristics: tuple[str, ...], count: int) -> str:
            return "\n".join(
                ":BEGIN\n"
                + "\n".join(
                    f'"{name}"\t{observation + index / 10}\t1\t1\t-1'
                    for index, name in enumerate(characteristics)
                )
                + "\n:END"
                for observation in range(1, count + 1)
            )

        system_a = report_blocks(("C1", "C2"), 3)
        system_b = report_blocks(("C1", "C2"), 3)
        analyses = parse_paired_multicharacteristic_measurements(
            StringIO(system_a), StringIO(system_b)
        )
        self.assertEqual(analyses["C1"]["paired_df"]["Observation"].tolist(), [1, 2, 3])

        with self.assertRaisesRegex(ValueError, "report blocks"):
            parse_paired_multicharacteristic_measurements(
                StringIO(system_a), StringIO(report_blocks(("C1", "C2"), 2))
            )

    def test_rejects_characteristics_missing_from_other_system(self) -> None:
        def reports(characteristics: tuple[str, ...]) -> str:
            return "\n".join(
                ":BEGIN\n"
                + "\n".join(f'"{name}"\t{value}\t1\t1\t-1' for name in characteristics)
                + "\n:END"
                for value in (1, 2)
            )

        with self.assertRaisesRegex(ValueError, "different characteristics"):
            parse_paired_multicharacteristic_measurements(
                StringIO(reports(("C1", "C2"))), StringIO(reports(("C1", "C3")))
            )


class PairedOverviewTests(unittest.TestCase):
    @staticmethod
    def _analysis(p_value: float, mean_difference: float = 1.0, stdev: float = 1.0) -> dict:
        return {
            "paired_df": pd.DataFrame(
                {"Observation": [1, 2], "System_A": [2.0, 3.0], "System_B": [1.0, 2.0], "Difference": [1.0, 1.0]}
            ),
            "metrics": {
                "N": 2,
                "Mean_D": mean_difference,
                "StDev_D": stdev,
                "CI_Lower": mean_difference - 0.5,
                "CI_Upper": mean_difference + 0.5,
                "P_Value": p_value,
            },
            "diagnostics": {
                "Outlier_Count": 0,
                "Outlier_Status": "PASS",
                "Normality_Status": "PASS",
                "Sample_Size_Status": "INFO",
            },
        }

    def test_overview_uses_holm_adjustment_and_sorts_by_adjusted_p(self) -> None:
        analyses = {
            "C1": self._analysis(0.01),
            "C2": self._analysis(0.04),
            "C3": self._analysis(0.03),
        }
        overview = build_paired_ttest_overview_dataframe(analyses)

        self.assertEqual(overview["Characteristic"].tolist(), ["C1", "C2", "C3"])
        self.assertEqual(overview["Holm P-Value"].tolist(), [0.03, 0.06, 0.06])
        self.assertIn("not evidence", create_paired_ttest_html_overview(overview, "A", "B"))

    def test_zero_variation_has_missing_standardized_effect(self) -> None:
        overview = build_paired_ttest_overview_dataframe(
            {"Constant": self._analysis(1.0, mean_difference=0.0, stdev=0.0)}
        )
        self.assertTrue(pd.isna(overview.loc[0, "Standardized Effect"]))
        self.assertEqual(overview.loc[0, "Conclusion"], "No significant difference detected")

    def test_zip_places_overview_first_and_uses_unique_safe_names(self) -> None:
        analyses = {"C1/A": self._analysis(0.01), "C1_A": self._analysis(0.02)}
        with patch(
            "gage_tracer.paired_ttest.create_paired_ttest_dashboard",
            side_effect=lambda paired_df, metrics, **kwargs: f"<html>{paired_df['Observation'].size}</html>",
        ) as dashboard_builder:
            archive_bytes = create_paired_ttest_html_zip(analyses, "System A", "System B")

        with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
            names = archive.namelist()
            self.assertEqual(names[0], "000_Paired_T_Test_Study_Overview.html")
            self.assertEqual(names[1:], ["001_Paired_T_Test_C1_A.html", "002_Paired_T_Test_C1_A.html"])
            self.assertIsNone(archive.testzip())
        self.assertEqual(
            [call.kwargs["characteristic_name"] for call in dashboard_builder.call_args_list],
            ["C1/A", "C1_A"],
        )


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
    def test_constant_nonzero_difference_diagnostic_matches_test(self) -> None:
        system_a = [2.0, 3.0, 4.0]
        system_b = [1.0, 2.0, 3.0]
        metrics = calculate_paired_ttest_metrics(system_a, system_b)
        diagnostics = calculate_paired_ttest_diagnostics(system_a, system_b)

        self.assertEqual(metrics["P_Value"], 0.0)
        self.assertEqual(diagnostics["Sample_Size_Status"], "PASS")

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
        report_html = create_paired_ttest_dashboard(
            paired_df, metrics, characteristic_name="C20"
        )

        for section in ("Summary Report", "Diagnostic Report", "Report Card"):
            self.assertIn(section, report_html)
        self.assertIn("Paired data in worksheet order", report_html)
        self.assertIn("Characteristic: C20", report_html)
        self.assertIn("Power and detectable difference analysis", report_html)
        self.assertEqual(report_html.count("data:image/png;base64,"), 7)


if __name__ == "__main__":
    unittest.main()
