"""Entry point for the Type 1 Gage Study pipeline.

This is the only script you need to run.  Drop your raw data file
as ``RAW DATA.txt`` in this folder and execute::

    python Type_1_gage_handy_tool.py

It will produce three output files in the same directory:

- ``gage data.txt``                     — parsed measurements (TSV)
- ``Gage_Study_Summary.txt``            — Minitab-style text report
- ``Gage_Study_Summary_dashboard.html`` — interactive HTML dashboard
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

# Root directory — everything is resolved relative to where this script lives.
PROJECT_ROOT: Path = Path(__file__).resolve().parent

# Add src/ to the import path so we can use the gage_tracer package
# without needing a pip install.
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from gage_tracer.data_parser import transform_ogp_data          # noqa: E402  # type: ignore[import-not-found]
from gage_tracer.calculations import calculate_type1_metrics     # noqa: E402  # type: ignore[import-not-found]
from gage_tracer.visualization import create_dashboard           # noqa: E402  # type: ignore[import-not-found]

# Structured directories for Type 1 output files.
GAGE_ROOT: Path = PROJECT_ROOT / "gage_type1"
GAGE_RAW_DIR: Path = GAGE_ROOT / "raw"
GAGE_DATA_DIR: Path = GAGE_ROOT / "data"
GAGE_REPORT_DIR: Path = GAGE_ROOT / "reports"
GAGE_DASHBOARD_DIR: Path = GAGE_ROOT / "dashboards"

RAW_FILE: Path = GAGE_RAW_DIR / "RAW DATA.txt"
ROOT_RAW_FILE: Path = PROJECT_ROOT / "RAW DATA.txt"
GAGE_DATA_FILE: Path = GAGE_DATA_DIR / "gage data.txt"
ROOT_GAGE_DATA_FILE: Path = PROJECT_ROOT / "gage data.txt"
SUMMARY_TXT: Path = GAGE_REPORT_DIR / "Gage_Study_Summary.txt"
ROOT_SUMMARY_TXT: Path = PROJECT_ROOT / "Gage_Study_Summary.txt"
DASHBOARD_HTML: Path = GAGE_DASHBOARD_DIR / "Gage_Study_Summary_dashboard.html"
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


def run() -> None:
    """Run the full pipeline: Parse → Calculate → Report → Dashboard.

    Steps:
        1. Parse raw OGP file into a structured TSV.
        2. Compute Type 1 Gage Study metrics for each dimension.
        3. Generate a text report and an interactive HTML dashboard.
    """
    print("=" * 50)
    print("  Type 1 Gage Study — Automated Report")
    print("=" * 50)

    # Ensure structured output directories exist.
    GAGE_RAW_DIR.mkdir(parents=True, exist_ok=True)
    GAGE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    GAGE_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    GAGE_DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    # Migrate legacy root outputs into structured dirs if needed.
    if not GAGE_DATA_FILE.exists() and ROOT_GAGE_DATA_FILE.exists():
        shutil.move(str(ROOT_GAGE_DATA_FILE), str(GAGE_DATA_FILE))
        print(f"      Migrated legacy parsed data to {GAGE_DATA_FILE.relative_to(PROJECT_ROOT)}")
    if not SUMMARY_TXT.exists() and ROOT_SUMMARY_TXT.exists():
        shutil.move(str(ROOT_SUMMARY_TXT), str(SUMMARY_TXT))
        print(f"      Migrated legacy report to {SUMMARY_TXT.relative_to(PROJECT_ROOT)}")
    if not DASHBOARD_HTML.exists() and ROOT_DASHBOARD_HTML.exists():
        shutil.move(str(ROOT_DASHBOARD_HTML), str(DASHBOARD_HTML))
        print(f"      Migrated legacy dashboard to {DASHBOARD_HTML.relative_to(PROJECT_ROOT)}")

    # Step 1 — Parse raw OGP data into a clean TSV table.
    if RAW_FILE.exists():
        raw_path = RAW_FILE
    elif ROOT_RAW_FILE.exists():
        raw_path = ROOT_RAW_FILE
        shutil.copy2(ROOT_RAW_FILE, RAW_FILE)
        print(f"      Migrated raw input to structured folder: {RAW_FILE.relative_to(PROJECT_ROOT)}")
    else:
        raw_path = None

    if raw_path is not None:
        print(f"\n[1/3] Parsing raw OGP data: {raw_path.name}")
        transform_ogp_data(raw_path, GAGE_DATA_FILE)
    else:
        print(f"\n[1/3] Raw OGP file not found ({RAW_FILE.name} or {ROOT_RAW_FILE.name});")
        print(f"      using existing {GAGE_DATA_FILE.relative_to(PROJECT_ROOT)}")

    if not GAGE_DATA_FILE.exists():
        print(f"ERROR: {GAGE_DATA_FILE.name} not found. Aborting.")
        return

    # Step 2 — Load the parsed data and compute Gage Study metrics.
    print(f"\n[2/3] Computing Type 1 Gage metrics …")
    df: pd.DataFrame = pd.read_csv(GAGE_DATA_FILE, sep="\t")

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
        print("No valid dimensions found in data.")
        return

    # Step 3 — Generate text report.
    _generate_text_report(summary, SUMMARY_TXT)
    print(f"     Report generated: {len(summary)} dimensions analyzed.")

    # Step 4 — Build the interactive HTML dashboard.
    print(f"\n[3/3] Generating dashboard …")
    create_dashboard(df, summary, DASHBOARD_HTML)

    print(f"\n{'=' * 50}")
    print(f"  [OK] Text report  → {SUMMARY_TXT.name}")
    print(f"  [OK] Dashboard    → {DASHBOARD_HTML.name}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    run()
