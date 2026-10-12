"""Legacy entry point for the paired-system comparison pipeline.

Prefer the unified command::

    msa paired [--system-a FILE] [--system-b FILE] [--output DIR]

Without arguments it reads the paired examples under ``data/examples/paired/``
and writes data, reports, and dashboards under ``outputs/paired/``.
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

from gage_tracer.paired_ttest import (
    build_paired_ttest_overview_dataframe,
    calculate_paired_ttest_diagnostics,
    parse_paired_measurements,
    parse_paired_multicharacteristic_measurements,
    export_paired_data,
    calculate_paired_ttest_metrics,
    create_paired_ttest_dashboard,
    create_paired_ttest_html_overview,
    create_paired_ttest_html_zip,
)
from gage_tracer.data_parser import paired_input_has_blocks

# Structured directories for paired T-Test files.
PAIRED_OUTPUTS_DIR: Path = PROJECT_ROOT / "outputs" / "paired"
PAIRED_EXAMPLES_DIR: Path = PROJECT_ROOT / "data" / "examples" / "paired"

PAIRED_RAW_DIR: Path = PAIRED_EXAMPLES_DIR
PAIRED_DATA_DIR: Path = PAIRED_OUTPUTS_DIR
PAIRED_REPORT_DIR: Path = PAIRED_OUTPUTS_DIR
PAIRED_DASHBOARD_DIR: Path = PAIRED_OUTPUTS_DIR

SYSTEM_A_FILE: Path = PAIRED_EXAMPLES_DIR / "PAIRED DATA SYSTEM A.txt"
SYSTEM_B_FILE: Path = PAIRED_EXAMPLES_DIR / "PAIRED DATA SYSTEM B.txt"
ROOT_SYSTEM_A_FILE: Path = PROJECT_ROOT / "PAIRED DATA SYSTEM A.txt"
ROOT_SYSTEM_B_FILE: Path = PROJECT_ROOT / "PAIRED DATA SYSTEM B.txt"
PAIRED_DATA_FILE: Path = PAIRED_OUTPUTS_DIR / "paired_data.txt"
ROOT_PAIRED_DATA_FILE: Path = PROJECT_ROOT / "paired_data.txt"
SUMMARY_TXT: Path = PAIRED_OUTPUTS_DIR / "Paired_T_Test_Summary.txt"
ROOT_SUMMARY_TXT: Path = PROJECT_ROOT / "Paired_T_Test_Summary.txt"
DASHBOARD_HTML: Path = PAIRED_OUTPUTS_DIR / "Paired_T_Test_Dashboard.html"
ROOT_DASHBOARD_HTML: Path = PROJECT_ROOT / "Paired_T_Test_Dashboard.html"


def _generate_text_report(
    metrics: dict[str, Any],
    output_path: Path,
    characteristic_name: str | None = None,
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
        if characteristic_name is not None:
            fh.write(f"Characteristic: {characteristic_name}\n")
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


def _safe_characteristic_filename(characteristic: str) -> str:
    return "".join(
        char if char.isalnum() or char in "-_" else "_"
        for char in characteristic
    ).strip("_") or "characteristic"


def _run_multicharacteristic(
    raw_a: Path,
    raw_b: Path,
    system_a_name: str,
    system_b_name: str,
    output_dir: Path,
) -> None:
    analyses = parse_paired_multicharacteristic_measurements(raw_a, raw_b)
    for analysis in analyses.values():
        analysis["metrics"] = calculate_paired_ttest_metrics(
            analysis["system_a"], analysis["system_b"]
        )
        analysis["diagnostics"] = calculate_paired_ttest_diagnostics(
            analysis["system_a"],
            analysis["system_b"],
            system_a_name=system_a_name,
            system_b_name=system_b_name,
        )

    overview = build_paired_ttest_overview_dataframe(analyses)
    overview_html_path = output_dir / "Paired_T_Test_Study_Overview.html"
    zip_path = output_dir / "Paired_T_Test_HTML_Reports.zip"
    create_paired_ttest_html_overview(
        overview, system_a_name, system_b_name, output_path=overview_html_path
    )
    zip_path.write_bytes(
        create_paired_ttest_html_zip(analyses, system_a_name, system_b_name)
    )

    data_frames: list[pd.DataFrame] = []
    for characteristic, analysis in analyses.items():
        characteristic_key = _safe_characteristic_filename(characteristic)
        paired_df = analysis["paired_df"].copy()
        paired_df.insert(1, "Characteristic", characteristic)
        data_frames.append(paired_df)
        _generate_text_report(
            analysis["metrics"],
            output_dir / f"Paired_T_Test_{characteristic_key}_Summary.txt",
            characteristic_name=characteristic,
        )
        create_paired_ttest_dashboard(
            analysis["paired_df"],
            analysis["metrics"],
            output_dir / f"Paired_T_Test_{characteristic_key}.html",
            system_a_name=system_a_name,
            system_b_name=system_b_name,
            characteristic_name=characteristic,
        )

    pd.concat(data_frames, ignore_index=True).to_csv(
        output_dir / PAIRED_DATA_FILE.name,
        sep="\t",
        index=False,
        float_format="%.8f",
    )
    overview_report = (
        "PAIRED T-TEST STUDY OVERVIEW\n"
        f"{system_a_name} compared with {system_b_name}\n"
        "Holm-adjusted p-values account for multiple characteristics. "
        "No significant difference detected is not evidence of equivalence.\n\n"
        + overview.to_string(index=False)
        + "\n"
    )
    (output_dir / "Paired_T_Test_Study_Overview.txt").write_text(
        overview_report, encoding="utf-8"
    )
    print(f"      [OK] Analysed {len(analyses)} characteristics")
    print(f"      [OK] Study overview -> {overview_html_path}")
    print(f"      [OK] All reports ZIP -> {zip_path}")


def run(
    system_a_file: Path | None = None,
    system_b_file: Path | None = None,
    output_dir: Path | None = None,
) -> int:
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

    use_legacy_defaults = (
        system_a_file is None and system_b_file is None and output_dir is None
    )
    output_path = Path(output_dir) if output_dir is not None else PAIRED_OUTPUTS_DIR
    output_path.mkdir(parents=True, exist_ok=True)
    paired_data_file = output_path / PAIRED_DATA_FILE.name
    summary_path = output_path / SUMMARY_TXT.name
    dashboard_path = output_path / DASHBOARD_HTML.name
    if system_a_file is None and system_b_file is None:
        PAIRED_RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Migrate legacy root outputs into structured dirs if needed.
    if use_legacy_defaults:
        if not paired_data_file.exists() and ROOT_PAIRED_DATA_FILE.exists():
            shutil.move(str(ROOT_PAIRED_DATA_FILE), str(paired_data_file))
            print(f"      Migrated legacy paired data to {paired_data_file}")
        if not summary_path.exists() and ROOT_SUMMARY_TXT.exists():
            shutil.move(str(ROOT_SUMMARY_TXT), str(summary_path))
            print(f"      Migrated legacy report to {summary_path}")
        if not dashboard_path.exists() and ROOT_DASHBOARD_HTML.exists():
            shutil.move(str(ROOT_DASHBOARD_HTML), str(dashboard_path))
            print(f"      Migrated legacy dashboard to {dashboard_path}")

    # Step 1 — Parse paired measurement files.
    if system_a_file is not None:
        raw_a = Path(system_a_file)
    elif SYSTEM_A_FILE.exists():
        raw_a = SYSTEM_A_FILE
    elif ROOT_SYSTEM_A_FILE.exists():
        raw_a = ROOT_SYSTEM_A_FILE
        if system_b_file is None:
            shutil.copy2(ROOT_SYSTEM_A_FILE, SYSTEM_A_FILE)
            print(f"      Migrated System A input to {SYSTEM_A_FILE}")
    else:
        raw_a = None

    if system_b_file is not None:
        raw_b = Path(system_b_file)
    elif SYSTEM_B_FILE.exists():
        raw_b = SYSTEM_B_FILE
    elif ROOT_SYSTEM_B_FILE.exists():
        raw_b = ROOT_SYSTEM_B_FILE
        if system_a_file is None:
            shutil.copy2(ROOT_SYSTEM_B_FILE, SYSTEM_B_FILE)
            print(f"      Migrated System B input to {SYSTEM_B_FILE}")
    else:
        raw_b = None

    if raw_a is None or not raw_a.is_file():
        raise FileNotFoundError(
            f"System A input file not found. Provide its path or place "
            f"{SYSTEM_A_FILE.name} in {PAIRED_RAW_DIR}."
        )
    if raw_b is None or not raw_b.is_file():
        raise FileNotFoundError(
            f"System B input file not found. Provide its path or place "
            f"{SYSTEM_B_FILE.name} in {PAIRED_RAW_DIR}."
        )

    print(f"\n[1/4] Parsing paired measurements...")
    print(f"      System A: {raw_a.name}")
    print(f"      System B: {raw_b.name}")

    try:
        if paired_input_has_blocks(raw_a) != paired_input_has_blocks(raw_b):
            raise ValueError("Both systems must use the same paired input format.")
        if paired_input_has_blocks(raw_a):
            system_a_name = raw_a.stem.replace("PAIRED DATA ", "")
            system_b_name = raw_b.stem.replace("PAIRED DATA ", "")
            _run_multicharacteristic(
                raw_a, raw_b, system_a_name, system_b_name, output_path
            )
            return 0
        paired_df, system_a, system_b, differences = parse_paired_measurements(
            raw_a, raw_b
        )
        print(f"      [OK] Loaded {len(system_a)} paired observations")
    except Exception as e:
        print(f"      [ERROR] Error parsing files: {e}")
        return 1

    # Step 2 — Export paired data to TSV.
    print(f"\n[2/4] Exporting paired data to TSV...")
    try:
        export_paired_data(paired_df, paired_data_file)
        print(f"      [OK] Data exported to {paired_data_file}")
    except Exception as e:
        print(f"      [ERROR] Error exporting: {e}")
        return 1

    # Step 3 — Compute paired t-test metrics.
    print(f"\n[3/4] Computing paired t-test metrics...")
    try:
        metrics = calculate_paired_ttest_metrics(system_a, system_b)
        print(f"      [OK] Metrics computed successfully")
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
        print(f"      [ERROR] Error in calculations: {e}")
        return 1

    # Step 4 — Generate text report.
    print(f"\n[4/4] Generating reports...")
    try:
        _generate_text_report(metrics, summary_path)
        print(f"      [OK] Text report -> {summary_path}")
    except Exception as e:
        print(f"      [ERROR] Error generating text report: {e}")
        return 1

    # Step 5 — Build the interactive HTML dashboard.
    try:
        create_paired_ttest_dashboard(paired_df, metrics, dashboard_path)
        print(f"      [OK] Dashboard -> {dashboard_path}")
    except Exception as e:
        print(f"      [ERROR] Error generating dashboard: {e}")
        return 1

    print(f"\n{'=' * 60}")
    print(f"  [SUCCESS]")
    print(f"{'=' * 60}")
    print(f"\nGenerated files:")
    print(f"  * {paired_data_file.name}")
    print(f"  * {summary_path.name}")
    print(f"  * {dashboard_path.name}")
    print(f"\nOpen the .html file in your browser to view the dashboard.\n")
    return 0


if __name__ == "__main__":
    run()
