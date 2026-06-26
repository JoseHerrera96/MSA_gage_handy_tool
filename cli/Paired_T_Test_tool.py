"""Entry point for the Paired T-Test comparison pipeline.

This script orchestrates the paired t-test analysis workflow:
1. Parse two measurement files (System A and System B)
2. Export paired data to a structured TSV
3. Calculate paired t-test metrics
4. Generate a text summary report
5. Create an interactive HTML dashboard

Usage:
    1. Place your System A measurements in a file named: PAIRED DATA SYSTEM A.txt
    2. Place your System B measurements in a file named: PAIRED DATA SYSTEM B.txt
    3. Run this script:

        python Paired_T_Test_tool.py

    4. Review the generated files:
       - paired_data.txt              — parsed measurements (TSV)
       - Paired_T_Test_Summary.txt    — text report
       - Paired_T_Test_Dashboard.html — interactive HTML dashboard
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

from gage_tracer.paired_ttest import (  # noqa: E402  # type: ignore[import-not-found]
    parse_paired_measurements,
    export_paired_data,
    calculate_paired_ttest_metrics,
    create_paired_ttest_dashboard,
)

# Structured directories for paired T-Test files.
PAIRED_ROOT: Path = PROJECT_ROOT / "paired_ttest"
PAIRED_RAW_DIR: Path = PAIRED_ROOT / "raw"
PAIRED_DATA_DIR: Path = PAIRED_ROOT / "data"
PAIRED_REPORT_DIR: Path = PAIRED_ROOT / "reports"
PAIRED_DASHBOARD_DIR: Path = PAIRED_ROOT / "dashboards"

SYSTEM_A_FILE: Path = PAIRED_RAW_DIR / "PAIRED DATA SYSTEM A.txt"
SYSTEM_B_FILE: Path = PAIRED_RAW_DIR / "PAIRED DATA SYSTEM B.txt"
ROOT_SYSTEM_A_FILE: Path = PROJECT_ROOT / "PAIRED DATA SYSTEM A.txt"
ROOT_SYSTEM_B_FILE: Path = PROJECT_ROOT / "PAIRED DATA SYSTEM B.txt"
PAIRED_DATA_FILE: Path = PAIRED_DATA_DIR / "paired_data.txt"
ROOT_PAIRED_DATA_FILE: Path = PROJECT_ROOT / "paired_data.txt"
SUMMARY_TXT: Path = PAIRED_REPORT_DIR / "Paired_T_Test_Summary.txt"
ROOT_SUMMARY_TXT: Path = PROJECT_ROOT / "Paired_T_Test_Summary.txt"
DASHBOARD_HTML: Path = PAIRED_DASHBOARD_DIR / "Paired_T_Test_Dashboard.html"
ROOT_DASHBOARD_HTML: Path = PROJECT_ROOT / "Paired_T_Test_Dashboard.html"


def _generate_text_report(
    metrics: dict[str, Any],
    output_path: Path,
) -> None:
    """Write a Minitab-style plain-text summary report.

    Formats all metric values to fixed decimal places for easy reading
    and reproducibility.

    Args:
        metrics: Dictionary returned by ``calculate_paired_ttest_metrics``.
        output_path: Where to save the ``.txt`` report.
    """
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("=" * 70 + "\n")
        fh.write("PAIRED T-TEST COMPARISON: SYSTEM A vs. SYSTEM B\n")
        fh.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        fh.write("=" * 70 + "\n\n")

        # Hypotheses
        fh.write("HYPOTHESES\n")
        fh.write("-" * 70 + "\n")
        fh.write(f"Null Hypothesis (H₀):        {metrics['H0']}\n")
        fh.write(f"Alternative Hypothesis (H₁): {metrics['HA']}\n")
        fh.write(f"\nTest Type: Two-sided paired t-test\n")
        fh.write(f"Significance Level (α):      0.05\n\n")

        # Descriptive Statistics
        fh.write("DESCRIPTIVE STATISTICS\n")
        fh.write("-" * 70 + "\n")
        fh.write(f"{'Statistic':<25} {'System A':>15} {'System B':>15} {'Difference':>15}\n")
        fh.write("-" * 70 + "\n")

        n = int(metrics["N"])
        fh.write(f"{'N':<25} {n:>15} {n:>15} {n:>15}\n")
        fh.write(
            f"{'Mean':<25} {float(metrics['Mean_A']):>15.8f} "
            f"{float(metrics['Mean_B']):>15.8f} {float(metrics['Mean_D']):>15.8f}\n"
        )
        fh.write(
            f"{'StDev':<25} {float(metrics['StDev_A']):>15.8f} "
            f"{float(metrics['StDev_B']):>15.8f} {float(metrics['StDev_D']):>15.8f}\n"
        )
        fh.write(
            f"{'SE Mean':<25} {float(metrics['SE_A']):>15.8f} "
            f"{float(metrics['SE_B']):>15.8f} {float(metrics['SE_D']):>15.8f}\n"
        )
        fh.write("\n")

        # T-Test Results
        fh.write("PAIRED T-TEST RESULTS\n")
        fh.write("-" * 70 + "\n")
        df = int(metrics["DF"])
        t_val = float(metrics["T_Value"])
        p_val = float(metrics["P_Value"])
        ci_lower = float(metrics["CI_Lower"])
        ci_upper = float(metrics["CI_Upper"])

        fh.write(f"Mean Difference (A − B):    {float(metrics['Mean_D']):>15.8f}\n")
        fh.write(f"95% Confidence Interval:    [{ci_lower:>15.8f}, {ci_upper:>15.8f}]\n")
        fh.write(f"T-Statistic:                {t_val:>15.6f}\n")
        fh.write(f"Degrees of Freedom:         {df:>15}\n")
        fh.write(f"P-Value (two-sided):        {p_val:>15.6f}\n\n")

        # Conclusion
        alpha = 0.05
        is_significant = p_val < alpha
        fh.write("CONCLUSION\n")
        fh.write("-" * 70 + "\n")
        if is_significant:
            fh.write(
                f"P-Value ({p_val:.6f}) < α (0.05): REJECT NULL HYPOTHESIS\n"
                f"Interpretation: The means of System A and System B are\n"
                f"statistically significantly different.\n"
            )
        else:
            fh.write(
                f"P-Value ({p_val:.6f}) >= α (0.05): FAIL TO REJECT NULL HYPOTHESIS\n"
                f"Interpretation: There is no statistically significant\n"
                f"difference between System A and System B.\n"
            )
        fh.write("\n" + "=" * 70 + "\n")


def run() -> None:
    """Run the full paired t-test pipeline.

    Steps:
        1. Parse paired measurement files.
        2. Export paired data to a structured TSV.
        3. Compute paired t-test metrics.
        4. Generate a text report and an interactive HTML dashboard.
    """
    print("=" * 60)
    print("  Paired T-Test Analysis — System A vs. System B")
    print("=" * 60)

    # Ensure structured output directories exist.
    PAIRED_RAW_DIR.mkdir(parents=True, exist_ok=True)
    PAIRED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PAIRED_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PAIRED_DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    # Migrate legacy root outputs into structured dirs if needed.
    if not PAIRED_DATA_FILE.exists() and ROOT_PAIRED_DATA_FILE.exists():
        shutil.move(str(ROOT_PAIRED_DATA_FILE), str(PAIRED_DATA_FILE))
        print(f"      Migrated legacy paired data to {PAIRED_DATA_FILE.relative_to(PROJECT_ROOT)}")
    if not SUMMARY_TXT.exists() and ROOT_SUMMARY_TXT.exists():
        shutil.move(str(ROOT_SUMMARY_TXT), str(SUMMARY_TXT))
        print(f"      Migrated legacy report to {SUMMARY_TXT.relative_to(PROJECT_ROOT)}")
    if not DASHBOARD_HTML.exists() and ROOT_DASHBOARD_HTML.exists():
        shutil.move(str(ROOT_DASHBOARD_HTML), str(DASHBOARD_HTML))
        print(f"      Migrated legacy dashboard to {DASHBOARD_HTML.relative_to(PROJECT_ROOT)}")

    # Step 1 — Parse paired measurement files.
    if SYSTEM_A_FILE.exists() and SYSTEM_B_FILE.exists():
        raw_a = SYSTEM_A_FILE
        raw_b = SYSTEM_B_FILE
    elif ROOT_SYSTEM_A_FILE.exists() and ROOT_SYSTEM_B_FILE.exists():
        raw_a = ROOT_SYSTEM_A_FILE
        raw_b = ROOT_SYSTEM_B_FILE
        shutil.copy2(ROOT_SYSTEM_A_FILE, SYSTEM_A_FILE)
        shutil.copy2(ROOT_SYSTEM_B_FILE, SYSTEM_B_FILE)
        print(f"      Migrated paired raw inputs to structured folder: {PAIRED_RAW_DIR}")
    else:
        print(f"\nERROR: Missing input files.")
        print(f"  Expected: {SYSTEM_A_FILE.name} and {SYSTEM_B_FILE.name} in {PAIRED_RAW_DIR}")
        if ROOT_SYSTEM_A_FILE.exists() or ROOT_SYSTEM_B_FILE.exists():
            print(f"  Or place both files in the repo root and rerun.")
        return

    print(f"\n[1/4] Parsing paired measurements...")
    print(f"      System A: {SYSTEM_A_FILE.name}")
    print(f"      System B: {SYSTEM_B_FILE.name}")

    try:
        paired_df, system_a, system_b, differences = parse_paired_measurements(
            SYSTEM_A_FILE, SYSTEM_B_FILE
        )
        print(f"      ✓ Loaded {len(system_a)} paired observations")
    except Exception as e:
        print(f"      ✗ Error parsing files: {e}")
        return

    # Step 2 — Export paired data to TSV.
    print(f"\n[2/4] Exporting paired data to TSV...")
    try:
        export_paired_data(paired_df, PAIRED_DATA_FILE)
        print(f"      ✓ Data exported to {PAIRED_DATA_FILE.relative_to(PROJECT_ROOT)}")
    except Exception as e:
        print(f"      ✗ Error exporting: {e}")
        return

    # Step 3 — Compute paired t-test metrics.
    print(f"\n[3/4] Computing paired t-test metrics...")
    try:
        metrics = calculate_paired_ttest_metrics(system_a, system_b)
        print(f"      ✓ Metrics computed successfully")
        print(
            f"        Mean Difference: {float(metrics['Mean_D']):+.8f}"
        )
        print(
            f"        T-Statistic: {float(metrics['T_Value']):.6f}"
        )
        print(
            f"        P-Value: {float(metrics['P_Value']):.6f}"
        )
    except Exception as e:
        print(f"      ✗ Error in calculations: {e}")
        return

    # Step 4 — Generate text report.
    print(f"\n[4/4] Generating reports...")
    try:
        _generate_text_report(metrics, SUMMARY_TXT)
        print(f"      ✓ Text report → {SUMMARY_TXT.relative_to(PROJECT_ROOT)}")
    except Exception as e:
        print(f"      ✗ Error generating text report: {e}")
        return

    # Step 5 — Build the interactive HTML dashboard.
    try:
        create_paired_ttest_dashboard(paired_df, metrics, DASHBOARD_HTML)
        print(f"      ✓ Dashboard → {DASHBOARD_HTML.relative_to(PROJECT_ROOT)}")
    except Exception as e:
        print(f"      ✗ Error generating dashboard: {e}")
        return

    print(f"\n{'=' * 60}")
    print(f"  [✓ SUCCESS]")
    print(f"{'=' * 60}")
    print(f"\nGenerated files:")
    print(f"  • {PAIRED_DATA_FILE.name}")
    print(f"  • {SUMMARY_TXT.name}")
    print(f"  • {DASHBOARD_HTML.name}")
    print(f"\nOpen the .html file in your browser to view the dashboard.\n")


if __name__ == "__main__":
    run()
