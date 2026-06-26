"""Example and validation script for the Paired T-Test module.

This script demonstrates how the paired t-test module works with a known,
simple dataset. It validates that:
1. Parsing works correctly
2. Calculations match expected values (ground truth)
3. Dashboard generation completes without errors

To run this example:
    python test_paired_ttest_example.py

It will create example input files, run the analysis, and verify the results.
"""

import sys
import tempfile
from pathlib import Path

# Add src/ to path
_src_dir = str(Path(__file__).resolve().parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import numpy as np
from gage_tracer.paired_ttest import (
    parse_paired_measurements,
    calculate_paired_ttest_metrics,
    export_paired_data,
    create_paired_ttest_dashboard,
)


def test_example_ground_truth():
    """Test with a known dataset and validate calculations.

    Ground Truth (calculated manually):
    - System A: [10.1, 10.3, 10.2, 10.4, 10.0]
    - System B: [10.0, 10.1, 10.3, 10.2, 10.1]
    - Differences: [0.1, 0.2, -0.1, 0.2, -0.1]
    - n = 5
    - Mean_D ≈ 0.06
    - StDev_D ≈ 0.1517
    - SE_D ≈ 0.0678
    - t ≈ 0.884 (df=4)
    - p ≈ 0.433 (two-sided)
    - 95% CI ≈ [-0.128, 0.248]
    """
    print("=" * 70)
    print("PAIRED T-TEST VALIDATION: Ground Truth Example")
    print("=" * 70 + "\n")

    # Create temporary directory
    tmpdir = Path(tempfile.gettempdir()) / "paired_ttest_example"
    tmpdir.mkdir(exist_ok=True)

    # Define test data
    system_a = [10.1, 10.3, 10.2, 10.4, 10.0]
    system_b = [10.0, 10.1, 10.3, 10.2, 10.1]

    # Write test files
    file_a = tmpdir / "SYSTEM_A.txt"
    file_b = tmpdir / "SYSTEM_B.txt"

    with open(file_a, "w") as f:
        f.write("\n".join(str(x) for x in system_a))

    with open(file_b, "w") as f:
        f.write("\n".join(str(x) for x in system_b))

    print(f"[1] Created test files in {tmpdir}\n")

    # Parse
    print("[2] Parsing paired measurements...")
    paired_df, sys_a, sys_b, diffs = parse_paired_measurements(file_a, file_b)
    print(f"    System A: {sys_a}")
    print(f"    System B: {sys_b}")
    print(f"    Differences: {diffs}\n")

    # Calculate metrics
    print("[3] Computing paired t-test metrics...")
    metrics = calculate_paired_ttest_metrics(sys_a, sys_b)

    # Extract key metrics
    n = int(metrics["N"])
    mean_d = float(metrics["Mean_D"])
    std_d = float(metrics["StDev_D"])
    se_d = float(metrics["SE_D"])
    t_val = float(metrics["T_Value"])
    p_val = float(metrics["P_Value"])
    ci_lower = float(metrics["CI_Lower"])
    ci_upper = float(metrics["CI_Upper"])

    print(f"\n    Results:")
    print(f"    ├─ N:                     {n}")
    print(f"    ├─ Mean Difference:       {mean_d:.8f}")
    print(f"    ├─ StDev Difference:      {std_d:.8f}")
    print(f"    ├─ SE Mean Difference:    {se_d:.8f}")
    print(f"    ├─ T-Statistic:           {t_val:.6f}")
    print(f"    ├─ Degrees of Freedom:    {int(metrics['DF'])}")
    print(f"    ├─ P-Value (two-sided):   {p_val:.6f}")
    print(f"    └─ 95% CI:                [{ci_lower:.8f}, {ci_upper:.8f}]\n")

    # Validate against known values
    print("[4] Validating against ground truth...")
    tolerance = 0.01  # Allow small numerical differences

    checks = [
        ("Mean_D", mean_d, 0.06),
        ("StDev_D", std_d, 0.1517),
        ("SE_D", se_d, 0.0678),
        ("T_Value", t_val, 0.884),
    ]

    all_pass = True
    for name, actual, expected in checks:
        rel_error = abs(actual - expected) / abs(expected) if expected != 0 else 0
        status = "✓ PASS" if rel_error < tolerance else "✗ FAIL"
        print(f"    {status}: {name:15} expected={expected:.6f}, actual={actual:.6f}")
        if rel_error >= tolerance:
            all_pass = False

    # P-value should be in reasonable range
    if 0.40 < p_val < 0.46:
        print(f"    ✓ PASS: P-Value in expected range (0.40-0.46, got {p_val:.6f})")
    else:
        print(f"    ✗ FAIL: P-Value out of range (expected 0.40-0.46, got {p_val:.6f})")
        all_pass = False

    print()

    # Export data
    print("[5] Exporting paired data...")
    paired_file = tmpdir / "paired_data.txt"
    export_paired_data(paired_df, paired_file)
    print(f"    ✓ Exported to {paired_file}\n")

    # Generate dashboard
    print("[6] Generating HTML dashboard...")
    dashboard_file = tmpdir / "Paired_T_Test_Dashboard.html"
    create_paired_ttest_dashboard(paired_df, metrics, dashboard_file)
    print(f"    ✓ Dashboard created at {dashboard_file}\n")

    # Summary
    print("=" * 70)
    if all_pass:
        print("✓ ALL VALIDATION CHECKS PASSED")
    else:
        print("✗ SOME VALIDATION CHECKS FAILED (see above)")
    print("=" * 70)
    print(f"\nGenerated files in: {tmpdir}")
    print(f"  • paired_data.txt")
    print(f"  • Paired_T_Test_Dashboard.html")
    print("\nExample complete!\n")


if __name__ == "__main__":
    test_example_ground_truth()
