"""Entry point for the Gage R&R (Crossed) ANOVA pipeline.

This is the CLI script for Gage R&R Crossed analysis. Drop your raw data file
as ``GAGE RR DATA.txt`` in the gage_rr/raw folder and execute::

    python Gage_RR_tool.py

It will produce three output files in the gage_rr directory:

- ``gage_rr/data/gage rr data.txt``         — parsed measurements (TSV)
- ``gage_rr/reports/Gage_RR_Summary.txt``   — Minitab-style text report
- ``gage_rr/dashboards/Gage_RR_Dashboard.html`` — 6-panel HTML dashboard
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

# Root directory — resolve the repository root from inside cli/.
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Add src/ to the import path so we can use the gage_tracer package
# without needing a pip install.
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from gage_tracer.data_parser import transform_gage_rr_data       # noqa: E402  # type: ignore[import-not-found]
from gage_tracer.calculations import calculate_gage_rr_crossed    # noqa: E402  # type: ignore[import-not-found]
from gage_tracer.visualization import create_gage_rr_dashboard     # noqa: E402  # type: ignore[import-not-found]

# Structured directories for Gage R&R output files.
GRR_ROOT: Path = PROJECT_ROOT / "gage_rr"
GRR_RAW_DIR: Path = GRR_ROOT / "raw"
GRR_DATA_DIR: Path = GRR_ROOT / "data"
GRR_REPORT_DIR: Path = GRR_ROOT / "reports"
GRR_DASHBOARD_DIR: Path = GRR_ROOT / "dashboards"

RAW_FILE: Path = GRR_RAW_DIR / "GAGE RR DATA.txt"
ROOT_RAW_FILE: Path = PROJECT_ROOT / "GAGE RR DATA.txt"
GRR_DATA_FILE: Path = GRR_DATA_DIR / "gage rr data.txt"
ROOT_GRR_DATA_FILE: Path = PROJECT_ROOT / "gage rr data.txt"
SUMMARY_TXT: Path = GRR_REPORT_DIR / "Gage_RR_Summary.txt"
ROOT_SUMMARY_TXT: Path = PROJECT_ROOT / "Gage_RR_Summary.txt"
DASHBOARD_HTML: Path = GRR_DASHBOARD_DIR / "Gage_RR_Dashboard.html"
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


def run() -> None:
    """Run the full Gage R&R Crossed pipeline: Parse → Calculate → Report → Dashboard.

    Steps:
        1. Parse raw data file (90 measurements) into structured TSV.
        2. Compute ANOVA and variance components.
        3. Generate text report and 6-panel HTML dashboard.
    """
    print("=" * 50)
    print("  Gage R&R (Crossed) — Automated Report")
    print("=" * 50)

    # Ensure structured output directories exist.
    GRR_RAW_DIR.mkdir(parents=True, exist_ok=True)
    GRR_DATA_DIR.mkdir(parents=True, exist_ok=True)
    GRR_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    GRR_DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    # Migrate legacy root outputs into structured dirs if needed.
    if not GRR_DATA_FILE.exists() and ROOT_GRR_DATA_FILE.exists():
        shutil.move(str(ROOT_GRR_DATA_FILE), str(GRR_DATA_FILE))
        print(f"      Migrated legacy parsed data to {GRR_DATA_FILE.relative_to(PROJECT_ROOT)}")
    if not SUMMARY_TXT.exists() and ROOT_SUMMARY_TXT.exists():
        shutil.move(str(ROOT_SUMMARY_TXT), str(SUMMARY_TXT))
        print(f"      Migrated legacy report to {SUMMARY_TXT.relative_to(PROJECT_ROOT)}")
    if not DASHBOARD_HTML.exists() and ROOT_DASHBOARD_HTML.exists():
        shutil.move(str(ROOT_DASHBOARD_HTML), str(DASHBOARD_HTML))
        print(f"      Migrated legacy dashboard to {DASHBOARD_HTML.relative_to(PROJECT_ROOT)}")

    # Step 1 — Parse raw data into a clean TSV table.
    if RAW_FILE.exists():
        raw_path = RAW_FILE
    elif ROOT_RAW_FILE.exists():
        raw_path = ROOT_RAW_FILE
        shutil.copy2(ROOT_RAW_FILE, RAW_FILE)
        print(f"      Migrated raw input to structured folder: {RAW_FILE.relative_to(PROJECT_ROOT)}")
    else:
        raw_path = None

    if raw_path is not None:
        print(f"\n[1/3] Parsing raw Gage R&R data: {raw_path.name}")
        try:
            df = transform_gage_rr_data(raw_path, GRR_DATA_FILE)
        except ValueError as e:
            print(f"ERROR: {e}")
            print("Please ensure the file contains exactly 90 measurements with NOMINAL, UPPER_TOL, and LOWER_TOL specifications.")
            return
    else:
        print(f"\n[1/3] Raw data file not found ({RAW_FILE.name} or {ROOT_RAW_FILE.name});")
        print(f"      using existing {GRR_DATA_FILE.relative_to(PROJECT_ROOT)}")

    if not GRR_DATA_FILE.exists():
        print(f"ERROR: {GRR_DATA_FILE.name} not found. Aborting.")
        return

    # Step 2 — Load the parsed data and compute Gage R&R metrics.
    print(f"\n[2/3] Computing Gage R&R ANOVA metrics …")
    df: pd.DataFrame = pd.read_csv(GRR_DATA_FILE, sep="\t")

    # Extract tolerance from DataFrame
    tolerance = df["Tolerance"].iloc[0]

    try:
        results = calculate_gage_rr_crossed(df, tolerance)
    except Exception as e:
        print(f"ERROR computing Gage R&R metrics: {e}")
        return

    # Step 3 — Generate text report.
    _generate_text_report(results, SUMMARY_TXT)
    print(f"     Report generated with {results['n_parts']} parts and {results['n_operators']} operators.")

    # Step 4 — Build the 6-panel HTML dashboard.
    print(f"\n[3/3] Generating 6-panel dashboard …")
    fig = create_gage_rr_dashboard(df, results)

    # Save figure as PNG
    import matplotlib.pyplot as plt
    dashboard_png = GRR_DASHBOARD_DIR / "Gage_RR_Dashboard.png"
    fig.savefig(dashboard_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"     Dashboard saved as PNG: {dashboard_png.name}")

    print(f"\n{'=' * 50}")
    print(f"  [OK] Text report  → {SUMMARY_TXT.name}")
    print(f"  [OK] Dashboard    → {dashboard_png.name}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    run()
