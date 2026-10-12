"""Legacy entry point for the Type 1 Gage Study pipeline.

Prefer the unified command::

    msa type1 [--input FILE] [--output DIR]

Without arguments it reads ``data/examples/type1/RAW DATA.txt`` and writes
the parsed data, summary, and dashboard under ``outputs/type1/``.
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd

# Root directory — resolve the repository root from inside cli/.
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

from gage_tracer.data_parser import transform_raw_data
from gage_tracer.calculations import calculate_type1_metrics
from gage_tracer.visualization import create_dashboard

# Structured directories for Type 1 files.
GAGE_OUTPUTS_DIR: Path = PROJECT_ROOT / "outputs" / "type1"
GAGE_EXAMPLES_DIR: Path = PROJECT_ROOT / "data" / "examples" / "type1"

GAGE_RAW_DIR: Path = GAGE_EXAMPLES_DIR
GAGE_DATA_DIR: Path = GAGE_OUTPUTS_DIR
GAGE_REPORT_DIR: Path = GAGE_OUTPUTS_DIR
GAGE_DASHBOARD_DIR: Path = GAGE_OUTPUTS_DIR

RAW_FILE: Path = GAGE_EXAMPLES_DIR / "RAW DATA.txt"
ROOT_RAW_FILE: Path = PROJECT_ROOT / "RAW DATA.txt"
GAGE_DATA_FILE: Path = GAGE_OUTPUTS_DIR / "gage data.txt"
ROOT_GAGE_DATA_FILE: Path = PROJECT_ROOT / "gage data.txt"
SUMMARY_TXT: Path = GAGE_OUTPUTS_DIR / "Gage_Study_Summary.txt"
ROOT_SUMMARY_TXT: Path = PROJECT_ROOT / "Gage_Study_Summary.txt"
DASHBOARD_HTML: Path = GAGE_OUTPUTS_DIR / "Gage_Study_Summary_dashboard.html"
ROOT_DASHBOARD_HTML: Path = PROJECT_ROOT / "Gage_Study_Summary_dashboard.html"


def _generate_text_report(
    summary: list[dict[str, Any]],
    output_path: Path,
) -> None:
    """Write a Minitab-style plain-text summary report.

    Formats all metric values to fixed decimal places for easy reading
    and comparison against Minitab output.

    Args:
        summary: List of metric dicts returned by ``calculate_type1_metrics``.
        output_path: Where to save the ``.txt`` report.
    """
    report_df = pd.DataFrame(summary)[
        [
            "Gage Item", "Reference", "Mean", "Bias", "T", "PValue",
            "StdDev", "6 x StdDev (SV)", "Tolerance (Tol)", "Max diff",
            "Cg", "Cgk", "%Var(Repeatability)",
            "%Var(Repeatability and Bias)", "Status",
        ]
    ].copy()

    for col in ["Reference", "Mean", "Bias", "StdDev",
                "6 x StdDev (SV)", "Tolerance (Tol)", "Max diff"]:
        report_df[col] = report_df[col].map(lambda x: f"{x:.8f}")
    for col in ["T", "PValue", "Cg", "Cgk"]:
        report_df[col] = report_df[col].map(lambda x: f"{x:.4f}")
    for col in ["%Var(Repeatability)", "%Var(Repeatability and Bias)"]:
        report_df[col] = report_df[col].map(
            lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A"
        )

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("==============================================\n")
        fh.write("AUTOMATED TYPE 1 GAGE STUDY (MINITAB-STYLE)\n")
        fh.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        fh.write("==============================================\n\n")
        fh.write(report_df.to_string(index=False))


def run(
    input_file: Path | None = None,
    output_dir: Path | None = None,
) -> None:
    """Run the full pipeline: Parse → Calculate → Report → Dashboard.

    Steps:
        1. Parse raw data file into a structured TSV.
        2. Compute Type 1 Gage Study metrics for each dimension.
        3. Generate a text report and an interactive HTML dashboard.
    """
    print("=" * 50)
    print("  Type 1 Gage Study — Automated Report")
    print("=" * 50)

    use_legacy_defaults = input_file is None and output_dir is None
    output_path = Path(output_dir) if output_dir is not None else GAGE_OUTPUTS_DIR
    data_file = output_path / GAGE_DATA_FILE.name
    summary_path = output_path / SUMMARY_TXT.name
    dashboard_path = output_path / DASHBOARD_HTML.name
    output_path.mkdir(parents=True, exist_ok=True)
    if input_file is None:
        GAGE_RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Migrate legacy root outputs into structured dirs if needed.
    if use_legacy_defaults:
        if not data_file.exists() and ROOT_GAGE_DATA_FILE.exists():
            shutil.move(str(ROOT_GAGE_DATA_FILE), str(data_file))
            print(f"      Migrated legacy parsed data to {data_file}")
        if not summary_path.exists() and ROOT_SUMMARY_TXT.exists():
            shutil.move(str(ROOT_SUMMARY_TXT), str(summary_path))
            print(f"      Migrated legacy report to {summary_path}")
        if not dashboard_path.exists() and ROOT_DASHBOARD_HTML.exists():
            shutil.move(str(ROOT_DASHBOARD_HTML), str(dashboard_path))
            print(f"      Migrated legacy dashboard to {dashboard_path}")

    # Step 1 — Parse raw data into a clean TSV table.
    if input_file is not None:
        raw_path = Path(input_file)
        if not raw_path.is_file():
            raise FileNotFoundError(f"Type 1 input file not found: {raw_path}")
    elif RAW_FILE.exists():
        raw_path = RAW_FILE
    elif ROOT_RAW_FILE.exists():
        raw_path = ROOT_RAW_FILE
        shutil.copy2(ROOT_RAW_FILE, RAW_FILE)
        print(f"      Migrated raw input to structured folder: {RAW_FILE}")
    else:
        raw_path = None

    if raw_path is not None:
        print(f"\n[1/3] Parsing raw data: {raw_path.name}")
        transform_raw_data(raw_path, data_file)
    else:
        print(f"\n[1/3] Raw data file not found ({RAW_FILE} or {ROOT_RAW_FILE});")
        print(f"      using existing {data_file}")

    if not data_file.exists():
        raise FileNotFoundError(f"Parsed Type 1 data file not found: {data_file}")
        return

    # Step 2 — Load the parsed data and compute Gage Study metrics.
    print(f"\n[2/3] Computing Type 1 Gage metrics ...")
    df: pd.DataFrame = pd.read_csv(data_file, sep="\t")

    # These columns are metadata/stats — everything else is a measurement dimension.
    _SKIP_COLS = {"", " ", "Dimension", "Average", "Max diff", "Nominal", "Upper Tol", "Lower Tol"}
    summary: list[dict[str, Any]] = []
    for col in df.columns:
        if col.strip() not in _SKIP_COLS:
            measurements = df[col].dropna().astype(float)
            if measurements.empty:
                continue
            try:
                spec_row = df[df["Dimension"] == col].iloc[0]
                summary.append(calculate_type1_metrics(col, measurements, spec_row))
            except (KeyError, IndexError, ValueError, TypeError):
                continue

    if not summary:
        raise ValueError("No valid dimensions found in the parsed Type 1 data.")

    # Step 3 — Generate text report.
    _generate_text_report(summary, summary_path)
    print(f"     Report generated: {len(summary)} dimensions analyzed.")

    # Step 4 — Build the interactive HTML dashboard.
    print(f"\n[3/3] Generating dashboard ...")
    create_dashboard(df, summary, dashboard_path)

    print(f"\n{'=' * 50}")
    print(f"  [OK] Text report  -> {summary_path}")
    print(f"  [OK] Dashboard    -> {dashboard_path}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    run()
