from pathlib import Path
import unittest
from unittest.mock import patch

from cli.command import main


class UnifiedCommandTests(unittest.TestCase):
    def test_type1_arguments_are_forwarded(self) -> None:
        input_file = Path("measurements.txt")
        output_dir = Path("reports")
        with patch("cli.command.run_type1", return_value=None) as run_type1:
            result = main(
                ["type1", "--input", str(input_file), "--output", str(output_dir)]
            )

        self.assertEqual(result, 0)
        run_type1.assert_called_once_with(input_file=input_file, output_dir=output_dir)

    def test_grr_arguments_include_input_format_and_report_order(self) -> None:
        input_file = Path("grr.txt")
        output_dir = Path("grr-output")
        with patch("cli.command.run_grr") as run_grr:
            result = main(
                [
                    "grr",
                    "--input",
                    str(input_file),
                    "--output",
                    str(output_dir),
                    "--input-format",
                    "blocks",
                    "--report-order",
                    "operator-major",
                ]
            )

        self.assertEqual(result, 0)
        run_grr.assert_called_once_with(
            input_format="blocks",
            report_order="operator-major",
            input_file=input_file,
            output_dir=output_dir,
        )

    def test_paired_arguments_and_failure_status_are_forwarded(self) -> None:
        system_a = Path("system-a.txt")
        system_b = Path("system-b.txt")
        output_dir = Path("paired-output")
        with patch("cli.command.run_paired", return_value=1) as run_paired:
            result = main(
                [
                    "paired",
                    "--system-a",
                    str(system_a),
                    "--system-b",
                    str(system_b),
                    "--output",
                    str(output_dir),
                ]
            )

        self.assertEqual(result, 1)
        run_paired.assert_called_once_with(
            system_a_file=system_a,
            system_b_file=system_b,
            output_dir=output_dir,
        )
