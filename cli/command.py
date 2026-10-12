from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from cli.Gage_RR_tool import RAW_FILE as GRR_DEFAULT_INPUT
from cli.Gage_RR_tool import run as run_grr
from cli.Paired_T_Test_tool import SYSTEM_A_FILE, SYSTEM_B_FILE
from cli.Paired_T_Test_tool import run as run_paired
from cli.Type_1_gage_handy_tool import RAW_FILE as TYPE1_DEFAULT_INPUT
from cli.Type_1_gage_handy_tool import run as run_type1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="msa",
        description="Run a Measurement Systems Analysis workflow.",
    )
    subparsers = parser.add_subparsers(dest="workflow", required=True)

    type1 = subparsers.add_parser("type1", help="Run a Type 1 Gage Study.")
    type1.add_argument(
        "--input",
        type=Path,
        help=f"Raw input file (default: {TYPE1_DEFAULT_INPUT}).",
    )
    type1.add_argument(
        "--output",
        type=Path,
        help="Directory for generated data, report, and dashboard.",
    )

    grr = subparsers.add_parser("grr", help="Run a crossed Gage R&R study.")
    grr.add_argument(
        "--input",
        type=Path,
        help=f"Raw input file (default: {GRR_DEFAULT_INPUT}).",
    )
    grr.add_argument(
        "--output",
        type=Path,
        help="Directory for generated data, reports, and dashboards.",
    )
    grr.add_argument(
        "--input-format",
        choices=("auto", "blocks", "continuous"),
        default="auto",
        help="Input layout (default: auto).",
    )
    grr.add_argument(
        "--report-order",
        choices=("part-major", "operator-major"),
        default="part-major",
        help="Factor order for untagged reports (default: part-major).",
    )

    paired = subparsers.add_parser("paired", help="Compare two paired systems.")
    paired.add_argument(
        "--system-a",
        type=Path,
        help=f"System A input file (default: {SYSTEM_A_FILE}).",
    )
    paired.add_argument(
        "--system-b",
        type=Path,
        help=f"System B input file (default: {SYSTEM_B_FILE}).",
    )
    paired.add_argument(
        "--output",
        type=Path,
        help="Directory for generated data, reports, and dashboards.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.workflow == "type1":
            return int(run_type1(input_file=args.input, output_dir=args.output) or 0)
        if args.workflow == "grr":
            run_grr(
                input_format=args.input_format,
                report_order=args.report_order,
                input_file=args.input,
                output_dir=args.output,
            )
            return 0
        if args.workflow == "paired":
            return run_paired(
                system_a_file=args.system_a,
                system_b_file=args.system_b,
                output_dir=args.output,
            )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"msa {args.workflow}: error: {exc}\n")

    parser.error(f"Unknown workflow: {args.workflow}")
    return 2
