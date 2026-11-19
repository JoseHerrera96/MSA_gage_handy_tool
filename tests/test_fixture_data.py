import math
from io import BytesIO, StringIO
from pathlib import Path
import unittest

import pandas as pd

from gage_tracer.calculations import calculate_gage_rr_by_characteristic, calculate_type1_metrics
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
    parse_paired_periodic_multicharacteristic_measurements,
    parse_paired_unstructured_measurements,
    calculate_paired_ttest_metrics,
)
from gage_tracer.presentation import build_type1_summary, format_float_columns


INPUT_EXAMPLES = Path(__file__).resolve().parents[1] / "data" / "examples" / "input_modes"


def example_source(path: Path, report_format: str):
    if report_format == "custom":
        return StringIO(normalize_custom_report_markers(path, "REPORT", "REPORT"))
    return path


class SyntheticFixtureTests(unittest.TestCase):
    def test_browser_type1_adapter_matches_existing_workflow(self) -> None:
        from browser_poc import load_examples
        from type1_browser_poc import analyze_type1
        from gage_tracer.presentation import build_type1_summary

        examples = load_examples()
        for report_format in ("blocks", "periodic", "custom"):
            with self.subTest(report_format=report_format):
                text = examples("type1", report_format)["type1.txt"]
                result = analyze_type1(text, report_format, "REPORT", "REPORT")
                source = StringIO(text)
                if report_format == "custom":
                    source = StringIO(normalize_custom_report_markers(source, "REPORT", "REPORT"))
                parser_format = "blocks" if report_format == "custom" else report_format
                expected_frame = transform_raw_data(source, input_format=parser_format)
                self.assertEqual(result["tsv"], expected_frame.to_csv(sep="\t", index=False))
                self.assertEqual(result["summary"], build_type1_summary(expected_frame))
                self.assertIn("data:image/png;base64,", result["html"])

        blocks = examples("type1", "blocks")["type1.txt"]
        custom = blocks.replace(":BEGIN", "START").replace(":END", "STOP")
        self.assertEqual(
            analyze_type1(blocks, "blocks")["summary"],
            analyze_type1(custom, "custom", "START", "STOP")["summary"],
        )
        with self.assertRaises(ValueError):
            analyze_type1("not a measurement", "periodic")
        with self.assertRaisesRegex(ValueError, "example.txt"):
            analyze_type1("no markers", "custom", "START", "STOP", "example.txt")

    def test_browser_type1_threshold_decisions(self) -> None:
        from browser_poc import load_examples
        from type1_browser_poc import analyze_type1

        text = load_examples()("type1", "periodic")["type1.txt"]
        for tolerance, expected in (("0.05590", "FAIL"), ("0.05595", "PASS")):
            with self.subTest(tolerance=tolerance):
                result = analyze_type1(text.replace("0.10000", tolerance), "periodic")
                self.assertEqual(result["metrics"]["cg_status"], expected)
                self.assertEqual(result["metrics"]["cgk_status"], expected)

    def test_browser_type1_large_multicharacteristic_input(self) -> None:
        from type1_browser_poc import analyze_type1

        lines = []
        for index in range(1000):
            lines.append(f"Diameter\t{10 + (index % 7 - 3) * 0.0007:.5f}\t10\t0.1\t-0.1")
            lines.append(f"Height\t{5 + (index % 9 - 4) * 0.0003:.5f}\t5\t0.1\t-0.1")
        text = "\n".join(lines) + "\n"
        frame = transform_raw_data(StringIO(text), input_format="periodic")
        result = analyze_type1(text, "periodic")
        self.assertEqual(result["summary"], build_type1_summary(frame))
        self.assertEqual(result["tsv"], frame.to_csv(sep="\t", index=False))
        self.assertEqual(result["observations"], [1000])
        self.assertEqual(result["metrics"]["dimensions"], 2)

    def test_browser_grr_adapter_assignments(self) -> None:
        from browser_poc import load_examples
        from grr_browser_poc import analyze_grr, grr_detail

        examples = load_examples()
        expected = None
        for report_format in ("blocks", "periodic", "custom"):
            for distribution, order in (("single", "part-major"), ("single", "operator-major"), ("parts", "part-major"), ("operators", "part-major")):
                with self.subTest(report_format=report_format, distribution=distribution, order=order):
                    files = list(examples("grr", report_format, distribution, order).items())
                    result = analyze_grr(files, report_format, distribution, order, "REPORT", "REPORT")
                    frame = result["frame"]
                    assignments = frame[["Part", "Operator", "Trial", "Characteristic", "Measurement"]].sort_values(
                        ["Part", "Operator", "Trial", "Characteristic"], ignore_index=True
                    )
                    self.assertEqual(frame["Report"].nunique(), 90)
                    if expected is None:
                        expected = assignments
                    else:
                        pd.testing.assert_frame_equal(assignments, expected)
                    self.assertEqual(len(result["results"]), 1)
                    self.assertEqual(
                        grr_detail(result, next(iter(result["results"])))["data"]["data"],
                        format_float_columns(frame).to_dict(orient="split")["data"],
                    )

        with self.assertRaises(ValueError):
            analyze_grr([], "periodic", "parts")

    def test_browser_paired_adapter_formats_and_alignment(self) -> None:
        from browser_poc import load_examples
        from paired_browser_poc import analyze_paired

        examples = load_examples()
        expected = None
        for report_format in ("blocks", "periodic", "custom"):
            with self.subTest(report_format=report_format):
                files = examples("paired", report_format)
                result = analyze_paired(files["system_a.txt"], files["system_b.txt"], report_format, "REPORT", "REPORT")
                values = {name: (analysis["system_a"], analysis["system_b"]) for name, analysis in result["analyses"].items()}
                if expected is None:
                    expected = values
                else:
                    self.assertEqual(values, expected)
                for analysis in result["analyses"].values():
                    self.assertEqual(analysis["metrics"], calculate_paired_ttest_metrics(analysis["system_a"], analysis["system_b"]))

        numeric = analyze_paired("1\n2\n3\n", "1.1\n2.2\n3.1\n", "periodic")
        self.assertEqual(next(iter(numeric["analyses"].values()))["metrics"]["N"], 3)
        with self.assertRaises(ValueError):
            analyze_paired("1\n2\n3\n", "1\n2\n", "periodic")

    def test_browser_local_runtime_allowlist(self) -> None:
        from browser_poc_server import pyodide_runtime_allowlist

        lock = {"info": {"version": "0.27.7"}, "packages": {
            "safe": {"file_name": "safe.whl"},
            "traversal": {"file_name": "../private.whl"},
            "unexpected": {"file_name": "notes.txt"},
        }}
        allowed = pyodide_runtime_allowlist(lock)
        self.assertIn("pyodide.mjs", allowed)
        self.assertIn("safe.whl", allowed)
        self.assertNotIn("../private.whl", allowed)
        self.assertNotIn("notes.txt", allowed)
        with self.assertRaises(ValueError):
            pyodide_runtime_allowlist({"info": {"version": "0.0"}, "packages": {}})

    def test_browser_local_runtime_rejects_corrupt_packages(self) -> None:
        import hashlib
        import json
        from tempfile import TemporaryDirectory
        from browser_poc_server import validate_pyodide_runtime

        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for name in ("pyodide.mjs", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip"):
                (directory / name).write_bytes(b"core")
            package = {"file_name": "safe.whl", "sha256": hashlib.sha256(b"correct").hexdigest(), "depends": []}
            lock = {"info": {"version": "0.27.7"}, "packages": {name: package for name in ("numpy", "pandas", "scipy", "matplotlib")}}
            (directory / "pyodide-lock.json").write_text(json.dumps(lock), encoding="utf-8")
            (directory / "safe.whl").write_bytes(b"incorrect")
            with self.assertRaisesRegex(ValueError, "checksum"):
                validate_pyodide_runtime(directory)
            (directory / "safe.whl").write_bytes(b"correct")
            self.assertIn("safe.whl", validate_pyodide_runtime(directory))

    def test_type1_dashboard_escapes_characteristic_names(self) -> None:
        from browser_poc import load_examples
        from type1_browser_poc import analyze_type1

        name = '<img src=x onerror=alert(1)>'
        text = load_examples()("type1", "periodic")["type1.txt"].replace("Diameter", name)
        html = analyze_type1(text, "periodic")["html"]
        self.assertNotIn(name, html)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", html)
        name = 'Gauge" autofocus onfocus="alert(1)'
        text = load_examples()("type1", "periodic")["type1.txt"].replace('"Diameter"', name)
        html = analyze_type1(text, "periodic")["html"]
        self.assertNotIn(name, html)
        self.assertIn("Gauge&quot; autofocus onfocus=&quot;alert(1)", html)

    def test_browser_reports_escape_user_labels(self) -> None:
        from browser_poc import load_examples
        from grr_browser_poc import analyze_grr, grr_export
        from paired_browser_poc import analyze_paired, paired_export

        name = '<img src=x onerror=alert(1)>'
        escaped = '&lt;img src=x onerror=alert(1)&gt;'
        examples = load_examples()
        grr_files = [(filename, text.replace('Diameter', name)) for filename, text in examples('grr', 'periodic').items()]
        grr = analyze_grr(grr_files, 'periodic', 'single')
        for export_format in ('overview', 'dashboard'):
            html = grr_export(grr, export_format, name)
            self.assertNotIn(name, html)
            self.assertIn(escaped, html)

        paired_files = examples('paired', 'periodic')
        paired = analyze_paired(
            paired_files['system_a.txt'].replace('Diameter', name),
            paired_files['system_b.txt'].replace('Diameter', name),
            'periodic', name_a=name + '.txt', name_b='System B.txt',
        )
        for export_format in ('overview', 'dashboard'):
            html = paired_export(paired, export_format, name)
            self.assertNotIn(name, html)
            self.assertIn(escaped, html)

    def test_browser_report_charts_have_dark_backgrounds(self) -> None:
        import base64
        import re
        import numpy as np
        from PIL import Image
        from browser_poc import load_examples
        from grr_browser_poc import analyze_grr, grr_export
        from paired_browser_poc import analyze_paired, paired_export
        from type1_browser_poc import analyze_type1

        examples = load_examples()
        type1 = analyze_type1(examples("type1", "periodic")["type1.txt"], "periodic")
        grr = analyze_grr(list(examples("grr", "periodic").items()), "periodic", "single")
        paired_files = examples("paired", "periodic")
        paired = analyze_paired(paired_files["system_a.txt"], paired_files["system_b.txt"], "periodic")
        reports = (
            (type1["html"], 1),
            (grr_export(grr, "dashboard", next(iter(grr["results"]))), 1),
            (paired_export(paired, "dashboard", next(iter(paired["analyses"]))), 7),
        )
        for html, expected_count in reports:
            images = re.findall(r"data:image/png;base64,([A-Za-z0-9+/=]+)", html)
            self.assertEqual(len(images), expected_count)
            for encoded in images:
                with Image.open(BytesIO(base64.b64decode(encoded))) as image:
                    pixels = image.convert("RGB").resize((64, 64))
                    self.assertLess(max(pixels.getpixel((0, 0))), 90)
                    bright = np.all(np.asarray(pixels) > 230, axis=2).sum()
                    self.assertLess(bright / (64 * 64), 0.15)

    def test_browser_proof_generates_all_study_reports(self) -> None:
        from browser_poc import run_browser_poc

        result = run_browser_poc()
        self.assertEqual(len(result["type1"]["frame"]["data"]), 20)
        self.assertTrue(result["type1"]["report"]["images"][0]["nonblank"])
        self.assertEqual(len(result["grr"]["frame"]["data"]), 90)
        self.assertEqual(len(result["grr"]["archive"]), 2)
        self.assertEqual(len(result["grr"]["archive"]["001_Gage_RR_Diameter_Dashboard.html"]["images"]), 1)
        self.assertEqual(set(result["paired"]["analyses"]), {"Diameter", "Height"})
        self.assertEqual(len(result["paired"]["archive"]), 3)
        for name in ("001_Paired_T_Test_Diameter.html", "002_Paired_T_Test_Height.html"):
            self.assertEqual(len(result["paired"]["archive"][name]["images"]), 7)

    def test_generated_examples_include_expected_custom_and_grouped_files(self) -> None:
        from gage_tracer.input_examples import build_input_examples

        custom_parts = build_input_examples("grr", "custom", "parts")
        self.assertEqual(len(custom_parts), 10)
        self.assertIn("part_10.txt", custom_parts)
        self.assertIn("REPORT", custom_parts["part_10.txt"])

        periodic_operators = build_input_examples("grr", "periodic", "operators")
        self.assertEqual(len(periodic_operators), 3)
        self.assertIn("operator_03.txt", periodic_operators)
        self.assertNotIn("REPORT", periodic_operators["operator_03.txt"])

    def test_generated_type1_and_paired_examples_match_across_formats(self) -> None:
        from gage_tracer.input_examples import build_input_examples

        type1_reference = None
        paired_reference = None
        for report_format in ("blocks", "periodic", "custom"):
            with self.subTest(report_format=report_format):
                type1_text = build_input_examples("type1", report_format)["type1.txt"]
                if report_format == "custom":
                    type1_text = normalize_custom_report_markers(StringIO(type1_text), "REPORT", "REPORT")
                parser_format = "blocks" if report_format == "custom" else report_format
                frame = transform_raw_data(StringIO(type1_text), input_format=parser_format)
                self.assertEqual(len(frame), 20)
                self.assertEqual(len(build_type1_summary(frame)), 1)
                if type1_reference is None:
                    type1_reference = frame
                else:
                    pd.testing.assert_frame_equal(type1_reference, frame)

                examples = build_input_examples("paired", report_format)
                system_a = StringIO(examples["system_a.txt"])
                system_b = StringIO(examples["system_b.txt"])
                if report_format == "blocks":
                    paired = parse_paired_multicharacteristic_measurements(system_a, system_b)
                elif report_format == "periodic":
                    paired = parse_paired_periodic_multicharacteristic_measurements(system_a, system_b)
                else:
                    paired = parse_paired_custom_measurements(system_a, system_b, "REPORT", "REPORT")
                measurements = {name: (result["system_a"], result["system_b"]) for name, result in paired.items()}
                self.assertEqual(set(measurements), {"Diameter", "Height"})
                self.assertTrue(all(len(values[0]) == len(values[1]) == 20 for values in measurements.values()))
                for values in measurements.values():
                    self.assertTrue(math.isfinite(calculate_paired_ttest_metrics(*values)["P_Value"]))
                if paired_reference is None:
                    paired_reference = measurements
                else:
                    self.assertEqual(paired_reference, measurements)

    def test_generated_grr_examples_preserve_design_assignments(self) -> None:
        from gage_tracer.input_examples import build_input_examples

        reference = None
        for report_format in ("blocks", "periodic", "custom"):
            parser_format = "continuous" if report_format == "periodic" else "blocks"
            for distribution, order in (("single", "part-major"), ("single", "operator-major"),
                                        ("parts", "part-major"), ("operators", "part-major")):
                with self.subTest(report_format=report_format, distribution=distribution, order=order):
                    examples = build_input_examples("grr", report_format, distribution, order)
                    files = []
                    for name, text in examples.items():
                        if report_format == "custom":
                            text = normalize_custom_report_markers(StringIO(text), "REPORT", "REPORT")
                        files.append((name, StringIO(text)))
                    if distribution == "single":
                        frame = transform_gage_rr_data(files[0][1], input_format=parser_format, report_order=order)
                    else:
                        group = "part" if distribution == "parts" else "operator"
                        frame = transform_gage_rr_grouped_data(files, group, input_format=parser_format)
                    self.assertEqual(frame["Report"].nunique(), 90)
                    self.assertIn("Diameter", calculate_gage_rr_by_characteristic(frame))
                    columns = [column for column in frame.columns if column != "Report"]
                    actual = frame[columns].sort_values(["Part", "Operator", "Trial", "Characteristic"]).reset_index(drop=True)
                    if reference is None:
                        reference = actual
                    else:
                        pd.testing.assert_frame_equal(reference, actual)

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
