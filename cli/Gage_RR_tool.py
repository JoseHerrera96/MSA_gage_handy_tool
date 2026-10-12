"""Legacy entry point for the crossed Gage R&R ANOVA pipeline.

Prefer the unified command::

    msa grr [--input FILE] [--output DIR] [--report-order part-major|operator-major]

Without arguments it reads ``data/examples/gage_rr/GAGE RR DATA.txt`` and
writes normalized data, reports, and dashboards under ``outputs/gage_rr/``.
"""

from __future__ import annotations

import shutil
import sys
import time
import argparse
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd

# Root directory — resolve the repository root from inside cli/.
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

from gage_tracer.data_parser import transform_gage_rr_data
from gage_tracer.calculations import calculate_gage_rr_by_characteristic
from gage_tracer.visualization import create_gage_rr_dashboard, create_gage_rr_html_dashboard

# Structured directories for Gage R&R files.
GRR_OUTPUTS_DIR: Path = PROJECT_ROOT / "outputs" / "gage_rr"
GRR_EXAMPLES_DIR: Path = PROJECT_ROOT / "data" / "examples" / "gage_rr"

GRR_RAW_DIR: Path = GRR_EXAMPLES_DIR
GRR_DATA_DIR: Path = GRR_OUTPUTS_DIR
GRR_REPORT_DIR: Path = GRR_OUTPUTS_DIR
GRR_DASHBOARD_DIR: Path = GRR_OUTPUTS_DIR

RAW_FILE: Path = GRR_EXAMPLES_DIR / "GAGE RR DATA.txt"
ROOT_RAW_FILE: Path = PROJECT_ROOT / "GAGE RR DATA.txt"
GRR_DATA_FILE: Path = GRR_OUTPUTS_DIR / "gage rr data.txt"
ROOT_GRR_DATA_FILE: Path = PROJECT_ROOT / "gage rr data.txt"
SUMMARY_TXT: Path = GRR_OUTPUTS_DIR / "Gage_RR_Summary.txt"
ROOT_SUMMARY_TXT: Path = PROJECT_ROOT / "Gage_RR_Summary.txt"
DASHBOARD_HTML: Path = GRR_OUTPUTS_DIR / "Gage_RR_Dashboard.html"
ROOT_DASHBOARD_HTML: Path = PROJECT_ROOT / "Gage_RR_Dashboard.html"


def _generate_text_report(
    results: dict[str, Any],
    output_path: Path,
) -> None:
    """Write a Minitab-style plain-text summary report for Gage R&R.

    Formats all ANOVA results, variance components, and evaluation metrics
    to fixed decimal places for easy reading and comparison against Minitab.

    Args:
        results: Results dictionary from calculate_gage_rr_crossed.
        output_path: Where to save the .txt report.
    """
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("=" * 60 + "\n")
        fh.write("  GAGE R&R (CROSSED) ANOVA ANALYSIS (MINITAB-STYLE)\n")
        fh.write(f"  Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        fh.write("=" * 60 + "\n\n")

        fh.write("STUDY DESIGN:\n")
        fh.write(f"  Parts: {results['n_parts']}\n")
        fh.write(f"  Operators: {results['n_operators']}\n")
        fh.write(f"  Trials per part: {results['n_trials']}\n")
        fh.write(f"  Total measurements: {results['n_parts'] * results['n_operators'] * results['n_trials']}\n")
        fh.write(f"  Tolerance: {results['tolerance']:.8f}\n\n")

        fh.write("KEY METRICS:\n")
        fh.write(f"  Total Gage R&R (% Study Variation): {results['total_grr_pct']:.4f}%\n")
        fh.write(f"  Number of Distinct Categories (NDC): {results['ndc']}\n")
        fh.write(f"  Study Variation (6*SD): {results['study_variation']:.8f}\n")
        fh.write(f"  Interaction Pooled: {'Yes' if results['pooled_interaction'] else 'No'}\n")
        fh.write(f"  Interaction P-value: {results['interaction_p_value']:.6f}\n\n")

        fh.write("-" * 60 + "\n")
        fh.write("ANOVA TABLE\n")
        fh.write("-" * 60 + "\n")
        anova_df = results["anova_table"]
        fh.write(anova_df.to_string(index=False) + "\n\n")

        fh.write("-" * 60 + "\n")
        fh.write("VARIANCE COMPONENTS\n")
        fh.write("-" * 60 + "\n")
        var_df = results["variance_components"]
        fh.write(var_df.to_string(index=False) + "\n\n")

        fh.write("-" * 60 + "\n")
        fh.write("GAGE EVALUATION\n")
        fh.write("-" * 60 + "\n")
        gage_eval_df = results["gage_evaluation"]
        fh.write(gage_eval_df.to_string(index=False) + "\n\n")

        # Industrial verdict
        grr_pct = results["total_grr_pct"]
        ndc = results["ndc"]
        if grr_pct < 10 and ndc >= 5:
            verdict = "PASS - Excellent"
        elif 10 <= grr_pct <= 30 and ndc >= 5:
            verdict = "MARGINAL - May be acceptable"
        else:
            verdict = "FAIL - Needs improvement"

        fh.write("=" * 60 + "\n")
        fh.write(f"VERDICT: {verdict}\n")
        fh.write("=" * 60 + "\n")


def _file_stem(characteristic: str) -> str:
    """Return a filesystem-safe stem for a characteristic report."""
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in characteristic)


def run(
    input_format: str = "auto",
    report_order: str = "part-major",
    input_file: Path | None = None,
    output_dir: Path | None = None,
) -> None:
    """Run the full multireport Gage R&R pipeline.

    Steps:
        1. Parse complete raw reports into structured TSV data.
        2. Compute an independent ANOVA per measurement characteristic.
        3. Generate a text report and 6-panel HTML dashboard per characteristic.
    """
    print("=" * 50)
    print("  Gage R&R (Crossed) — Automated Report")
    print("=" * 50)

    use_legacy_defaults = input_file is None and output_dir is None
    output_path = Path(output_dir) if output_dir is not None else GRR_OUTPUTS_DIR
    data_file = output_path / GRR_DATA_FILE.name
    output_path.mkdir(parents=True, exist_ok=True)
    if input_file is None:
        GRR_RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Migrate legacy root outputs into structured dirs if needed.
    if use_legacy_defaults:
        if not data_file.exists() and ROOT_GRR_DATA_FILE.exists():
            shutil.move(str(ROOT_GRR_DATA_FILE), str(data_file))
            print(f"      Migrated legacy parsed data to {data_file}")
        if not SUMMARY_TXT.exists() and ROOT_SUMMARY_TXT.exists():
            shutil.move(str(ROOT_SUMMARY_TXT), str(SUMMARY_TXT))
            print(f"      Migrated legacy report to {SUMMARY_TXT}")
        if not DASHBOARD_HTML.exists() and ROOT_DASHBOARD_HTML.exists():
            shutil.move(str(ROOT_DASHBOARD_HTML), str(DASHBOARD_HTML))
            print(f"      Migrated legacy dashboard to {DASHBOARD_HTML}")

    # Step 1 — Parse raw data into a clean TSV table.
    if input_file is not None:
        raw_path = Path(input_file)
        if not raw_path.is_file():
            raise FileNotFoundError(f"Gage R&R input file not found: {raw_path}")
    elif RAW_FILE.exists():
        raw_path = RAW_FILE
    elif ROOT_RAW_FILE.exists():
        raw_path = ROOT_RAW_FILE
        shutil.copy2(ROOT_RAW_FILE, RAW_FILE)
        print(f"      Migrated raw input to structured folder: {RAW_FILE}")
    else:
        raw_path = None

    if raw_path is not None:
        print(f"\n[1/3] Parsing raw Gage R&R data: {raw_path.name}")
        try:
            df = transform_gage_rr_data(
                raw_path,
                data_file,
                input_format=input_format,
                report_order=report_order,
            )
        except ValueError as e:
            raise ValueError(
                f"{e} The input must contain exactly 90 report blocks: "
                "10 parts x 3 operators x 3 trials."
            ) from e
    else:
        print(f"\n[1/3] Raw data file not found ({RAW_FILE.name} or {ROOT_RAW_FILE.name});")
        print(f"      using existing {data_file}")

    if not data_file.exists():
        raise FileNotFoundError(f"Parsed Gage R&R data file not found: {data_file}")

    # Step 2 — Load the parsed data and compute Gage R&R metrics.
    print(f"\n[2/3] Computing Gage R&R ANOVA metrics ...")
    df: pd.DataFrame = pd.read_csv(data_file, sep="\t")

    try:
        all_results = calculate_gage_rr_by_characteristic(df)
    except Exception as e:
        raise RuntimeError(f"Error computing Gage R&R metrics: {e}") from e

    # Step 3/4 — Generate an independent report and dashboard per characteristic.
    print(f"\n[3/3] Generating {len(all_results)} characteristic reports ...")
    import matplotlib.pyplot as plt
    for characteristic, results in all_results.items():
        stem = _file_stem(characteristic)
        report_path = output_path / f"Gage_RR_Summary_{stem}.txt"
        dashboard_path = output_path / f"Gage_RR_Dashboard_{stem}.html"
        dashboard_png = output_path / f"Gage_RR_Dashboard_{stem}.png"
        characteristic_df = df[df["Characteristic"] == characteristic]

        _generate_text_report(results, report_path)
        fig = create_gage_rr_dashboard(characteristic_df, results)
        fig.savefig(dashboard_png, dpi=150, bbox_inches="tight")
        plt.close(fig)
        create_gage_rr_html_dashboard(characteristic_df, results, dashboard_path)
        print(f"     [{characteristic}] {report_path.name} | {dashboard_path.name}")

    print(f"\n{'=' * 50}")
    print(f"  [OK] Generated {len(all_results)} independent Gage R&R reports")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the fixed 90-block crossed Gage R&R analysis.")
    parser.add_argument(
        "--input-format",
        choices=("auto", "blocks", "continuous"),
        default="auto",
        help="Input layout: BEGIN/END blocks, continuous repeated rows, or auto-detect.",
    )
    parser.add_argument(
        "--report-order",
        choices=("part-major", "operator-major"),
        default="part-major",
        help=(
            "Factor nesting for untagged reports: Part -> Operator -> Trial "
            "(default) or Operator -> Part -> Trial."
        ),
    )
    parser.add_argument("--input", type=Path, help="Raw Gage R&R input file.")
    parser.add_argument("--output", type=Path, help="Directory for generated reports.")
    args = parser.parse_args()
    run(
        input_format=args.input_format,
        report_order=args.report_order,
        input_file=args.input,
        output_dir=args.output,
    )
