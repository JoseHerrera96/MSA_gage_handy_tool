import math
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from gage_tracer.calculations import calculate_type1_metrics
from gage_tracer.data_parser import (
    normalize_custom_report_markers,
    transform_gage_rr_data,
    transform_gage_rr_grouped_data,
    transform_raw_data,
)
from gage_tracer.paired_ttest import (
    parse_paired_custom_measurements,
    parse_paired_measurements,
    parse_paired_multicharacteristic_measurements,
    parse_paired_unstructured_measurements,
)


INPUT_EXAMPLES = Path(__file__).resolve().parents[1] / "data" / "examples" / "input_modes"


def example_source(path: Path, report_format: str):
    if report_format == "custom":
        return StringIO(normalize_custom_report_markers(path, "REPORT", "REPORT"))
    return path


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

    def test_type1_input_mode_examples_are_equivalent(self) -> None:
        frames = []
        for report_format in ("blocks", "periodic", "custom"):
            path = INPUT_EXAMPLES / "type1" / f"{report_format}.txt"
            source = example_source(path, report_format)
            parser_format = "blocks" if report_format == "custom" else report_format
            frames.append(transform_raw_data(source, input_format=parser_format))
        self.assertEqual(len(frames[0]), 20)
        for frame in frames[1:]:
            pd.testing.assert_frame_equal(frames[0], frame)

    def test_grr_input_mode_examples_are_equivalent(self) -> None:
        expected = None
        for report_format in ("blocks", "periodic", "custom"):
            directory = INPUT_EXAMPLES / "gage_rr" / report_format
            parser_format = {"blocks": "blocks", "periodic": "continuous", "custom": "blocks"}[report_format]
            single = transform_gage_rr_data(
                example_source(directory / "single.txt", report_format),
                input_format=parser_format,
            )
            for group, count in (("part", 10), ("operator", 3)):
                paths = sorted((directory / f"{group}s").glob("*.txt"))
                self.assertEqual(len(paths), count)
                files = [(path.name, example_source(path, report_format)) for path in paths]
                grouped = transform_gage_rr_grouped_data(files, group, input_format=parser_format)
                columns = [column for column in single.columns if column != "Report"]
                sort_columns = ["Part", "Operator", "Trial", "Characteristic"]
                actual = grouped[columns].sort_values(sort_columns).reset_index(drop=True)
                reference = single[columns].sort_values(sort_columns).reset_index(drop=True)
                pd.testing.assert_frame_equal(reference, actual)
            self.assertEqual(single["Report"].nunique(), 90)
            if expected is None:
                expected = single
            else:
                pd.testing.assert_frame_equal(expected, single)

    def test_paired_input_mode_examples_are_equivalent(self) -> None:
        paired = INPUT_EXAMPLES / "paired"
        blocks = parse_paired_measurements(paired / "blocks/system_a.txt", paired / "blocks/system_b.txt")
        periodic = parse_paired_unstructured_measurements(
            paired / "periodic/system_a.txt", paired / "periodic/system_b.txt"
        )
        custom = parse_paired_custom_measurements(
            paired / "custom/system_a.txt", paired / "custom/system_b.txt", "REPORT", "REPORT"
        )["__custom_numeric_series__"]
        self.assertEqual(len(blocks[1]), 20)
        self.assertEqual(blocks[1:3], periodic[1:3])
        self.assertEqual(blocks[1], custom["system_a"])
        self.assertEqual(blocks[2], custom["system_b"])

        structured = parse_paired_multicharacteristic_measurements(
            paired / "blocks/multicharacteristic_a.txt", paired / "blocks/multicharacteristic_b.txt"
        )
        custom_tabular = parse_paired_custom_measurements(
            paired / "custom/multicharacteristic_a.txt",
            paired / "custom/multicharacteristic_b.txt",
            "REPORT",
            "REPORT",
        )
        self.assertEqual(set(structured), set(custom_tabular))
        for characteristic in structured:
            self.assertEqual(structured[characteristic]["system_a"], custom_tabular[characteristic]["system_a"])
            self.assertEqual(structured[characteristic]["system_b"], custom_tabular[characteristic]["system_b"])

    def test_paired_custom_view_passes_marker_configuration_to_parser(self) -> None:
        from app.views import paired_view

        streamlit = MagicMock()
        streamlit.radio.return_value = "Customized"
        streamlit.columns.side_effect = lambda count: [MagicMock() for _ in range(count)]
        streamlit.text_input.return_value = "REPORT"
        file_a = MagicMock(name="system_a")
        file_a.name = "system_a.txt"
        file_a.getvalue.return_value = b"REPORT\n1\nREPORT"
        file_b = MagicMock(name="system_b")
        file_b.name = "system_b.txt"
        file_b.getvalue.return_value = b"REPORT\n2\nREPORT"
        streamlit.file_uploader.side_effect = [file_a, file_b]
        with patch.object(paired_view, "st", streamlit), \
             patch.object(paired_view, "parse_paired_custom_measurements", side_effect=ValueError("probe")) as parser, \
             patch.object(paired_view, "show_processing_error"):
            paired_view.render_paired_page()

        self.assertEqual(parser.call_count, 1)
        self.assertEqual(parser.call_args.args[2:], ("REPORT", "REPORT"))

    def test_paired_view_routes_periodic_tabular_rows_by_characteristic(self) -> None:
        from app.views import paired_view

        for mode in ("Periodic reports without markers", "BEGIN/END markers"):
            with self.subTest(mode=mode):
                streamlit = MagicMock()
                streamlit.radio.return_value = mode
                streamlit.columns.side_effect = lambda count: [MagicMock() for _ in range(count)]
                file_a = MagicMock(name="system_a")
                file_a.name = "system_a.txt"
                file_a.getvalue.return_value = b"C1\t1.1\t1\t0.1\t-0.1\nC1\t1.2"
                file_b = MagicMock(name="system_b")
                file_b.name = "system_b.txt"
                file_b.getvalue.return_value = b"C1\t1.0\nC1\t1.1\t1\t0.1\t-0.1"
                streamlit.file_uploader.side_effect = [file_a, file_b]
                with patch.object(paired_view, "st", streamlit), \
                     patch.object(paired_view, "parse_paired_periodic_multicharacteristic_measurements", wraps=paired_view.parse_paired_periodic_multicharacteristic_measurements) as parser, \
                     patch.object(paired_view, "calculate_paired_ttest_metrics", side_effect=ValueError("probe")), \
                     patch.object(paired_view, "show_processing_error"):
                    paired_view.render_paired_page()
                self.assertEqual(parser.call_count, 1)
