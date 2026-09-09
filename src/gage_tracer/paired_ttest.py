"""Paired T-Test analysis module for system-to-system measurement comparison.

This module performs paired comparison studies between two measurement systems
(e.g., System A vs. System B). It computes t-statistics, p-values, confidence
intervals, and generates a Minitab-grade HTML dashboard with embedded charts.

Design Philosophy:
- Pure, testable calculations (no I/O, no side effects).
- Follows the same architecture as the Type 1 Gage Study module.
- All formulas validated against industry standards (Minitab, SAS/JMP).
"""

from __future__ import annotations

import math
from io import BytesIO, StringIO, TextIOBase
from pathlib import Path
from typing import Any, IO, TextIO, Union

import base64
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from scipy.optimize import brentq

_InputSource = Union[Path, str, TextIO, IO[bytes]]

matplotlib.use("Agg")


# ---------------------------------------------------------------------------
# Data Parsing
# ---------------------------------------------------------------------------

def _read_text_lines(input_file: _InputSource) -> list[str]:
    """Read text lines from a path or an in-memory text/binary stream."""
    if isinstance(input_file, (Path, str)):
        with open(input_file, "r", encoding="utf-8") as fh:
            return [line.rstrip("\n") for line in fh]

    if hasattr(input_file, "read"):
        if isinstance(input_file, (StringIO, TextIOBase)):
            try:
                input_file.seek(0)
            except Exception:
                pass
            return [line.rstrip("\n") for line in input_file]

        raw = input_file.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        return raw.splitlines()

    raise TypeError("input_file must be a path or a text/binary stream")


def parse_paired_measurements(
    file_a: _InputSource,
    file_b: _InputSource,
) -> tuple[pd.DataFrame, list[float], list[float], list[float]]:
    """Parse two measurement sources and produce an aligned paired DataFrame.

    Both sources are expected to contain one measurement per line (numeric values).
    They must have the same number of observations. Each line is stripped and
    converted to float.

    Args:
        file_a: Path, filename, or in-memory text/binary stream for System A.
        file_b: Path, filename, or in-memory text/binary stream for System B.

    Returns:
        A tuple ``(paired_df, system_a_vals, system_b_vals, differences)``:
        - paired_df: DataFrame with columns [Observation, System_A, System_B, Difference].
        - system_a_vals: List of System A measurements.
        - system_b_vals: List of System B measurements.
        - differences: List of differences (A - B).

    Raises:
        ValueError: If the sources have different lengths or contain non-numeric data.
    """
    lines_a = [line.strip() for line in _read_text_lines(file_a) if line.strip()]
    system_a_vals = []
    for line in lines_a:
        try:
            system_a_vals.append(float(line))
        except ValueError:
            continue

    lines_b = [line.strip() for line in _read_text_lines(file_b) if line.strip()]
    system_b_vals = []
    for line in lines_b:
        try:
            system_b_vals.append(float(line))
        except ValueError:
            continue

    if len(system_a_vals) != len(system_b_vals):
        raise ValueError(
            f"Mismatched lengths: System A has {len(system_a_vals)} values, "
            f"System B has {len(system_b_vals)} values."
        )

    differences = [a - b for a, b in zip(system_a_vals, system_b_vals)]
    obs_nums = list(range(1, len(system_a_vals) + 1))
    paired_df = pd.DataFrame({
        "Observation": obs_nums,
        "System_A": system_a_vals,
        "System_B": system_b_vals,
        "Difference": differences,
    })

    return paired_df, system_a_vals, system_b_vals, differences


def export_paired_data(
    paired_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Export the paired measurements DataFrame to a tab-separated file.

    Args:
        paired_df: DataFrame with Observation, System_A, System_B, Difference.
        output_path: Path where the TSV will be written.
    """
    # Format numeric columns to 8 decimal places
    fmt_df = paired_df.copy()
    for col in ["System_A", "System_B", "Difference"]:
        fmt_df[col] = fmt_df[col].map(lambda x: f"{float(x):.8f}")

    fmt_df.to_csv(output_path, sep="\t", index=False)


# ---------------------------------------------------------------------------
# Statistical Calculations (Pure)
# ---------------------------------------------------------------------------

def calculate_paired_ttest_metrics(
    system_a: list[float],
    system_b: list[float],
) -> dict[str, object]:
    """Compute all paired t-test metrics matching Minitab standards.

    Given two paired samples, compute:
    - Descriptive statistics (N, Mean, StDev, SE Mean)
    - T-statistic and P-value (two-sided test, H0: μ_diff = 0)
    - 95% confidence interval for the mean difference
    - Hypothesis strings

    Args:
        system_a: List of System A measurements.
        system_b: List of System B measurements.

    Returns:
        Dict with all computed metrics: N, means, standard deviations,
        standard errors, t-value, p-value, confidence intervals, etc.
    """
    n = len(system_a)
    if n != len(system_b):
        raise ValueError(f"Length mismatch: {n} vs {len(system_b)}")
    if n < 2:
        raise ValueError("At least 2 paired observations required.")

    # Convert to numpy arrays
    a = np.array(system_a, dtype=float)
    b = np.array(system_b, dtype=float)
    d = a - b

    # Descriptive statistics
    mean_a = float(np.mean(a))
    mean_b = float(np.mean(b))
    mean_d = float(np.mean(d))

    # Sample standard deviations (ddof=1 for Bessel's correction)
    std_a = float(np.std(a, ddof=1))
    std_b = float(np.std(b, ddof=1))
    std_d = float(np.std(d, ddof=1))

    # Standard errors
    se_a = std_a / math.sqrt(n)
    se_b = std_b / math.sqrt(n)
    se_d = std_d / math.sqrt(n)

    # T-test: H0: μ_d = 0
    df = n - 1
    if std_d > 0:
        t_value = mean_d / se_d
    else:
        # If std_d == 0, all differences are identical
        t_value = float("inf") if abs(mean_d) > 1e-12 else 0.0

    # Two-sided p-value
    p_value = 2.0 * sp_stats.t.sf(abs(t_value), df)

    # 95% confidence interval for mean difference
    t_crit = sp_stats.t.ppf(0.975, df)  # Two-tailed, α=0.05
    ci_lower = mean_d - t_crit * se_d
    ci_upper = mean_d + t_crit * se_d

    return {
        "N": n,
        "Mean_A": mean_a,
        "Mean_B": mean_b,
        "Mean_D": mean_d,
        "StDev_A": std_a,
        "StDev_B": std_b,
        "StDev_D": std_d,
        "SE_A": se_a,
        "SE_B": se_b,
        "SE_D": se_d,
        "T_Value": float(t_value),
        "DF": df,
        "P_Value": float(p_value),
        "CI_Lower": float(ci_lower),
        "CI_Upper": float(ci_upper),
        "CI_Level": 0.95,
        "H0": "μ_A = μ_B (or equivalently, μ_Difference = 0)",
        "HA": "μ_A ≠ μ_B (two-sided)",
    }


def calculate_paired_ttest_diagnostics(
    system_a: list[float],
    system_b: list[float],
    system_a_name: str = "System A",
    system_b_name: str = "System B",
) -> dict[str, object]:
    """Evaluate normality, severe outliers, and sample-size adequacy.

    The checks apply to paired differences, the quantity assumed to be
    normally distributed by a paired t-test.
    """
    if len(system_a) != len(system_b):
        raise ValueError(f"Length mismatch: {len(system_a)} vs {len(system_b)}")
    if len(system_a) < 2:
        raise ValueError("At least 2 paired observations required.")

    differences = np.asarray(system_a, dtype=float) - np.asarray(system_b, dtype=float)
    sample_size = len(differences)
    mean_difference = float(np.mean(differences))
    std_difference = float(np.std(differences, ddof=1))
    if std_difference > 0:
        outlier_mask = np.abs(differences - mean_difference) > 3 * std_difference
    else:
        outlier_mask = np.zeros(sample_size, dtype=bool)

    normality_statistic: float | None = None
    normality_critical_value: float | None = None
    if sample_size >= 20:
        normality_status = "PASS"
        normality_message = (
            "Because your sample size is at least 20, normality is not an issue. "
            "The test is accurate with nonnormal data when the sample size is large enough."
        )
    elif sample_size >= 3 and std_difference > 0:
        try:
            anderson_result = sp_stats.anderson(
                differences, dist="norm", method="interpolate"
            )
        except TypeError:
            anderson_result = sp_stats.anderson(differences, dist="norm")
        normality_statistic = float(anderson_result.statistic)
        if hasattr(anderson_result, "pvalue"):
            normality_critical_value = 0.05
            normality_status = (
                "PASS" if float(anderson_result.pvalue) >= normality_critical_value else "WARNING"
            )
        else:
            critical_index = list(anderson_result.significance_level).index(5.0)
            normality_critical_value = float(anderson_result.critical_values[critical_index])
            normality_status = (
                "PASS" if normality_statistic <= normality_critical_value else "WARNING"
            )
        normality_message = (
            "Because your sample size is at least 20, normality is not an issue. "
            "The test is accurate with nonnormal data when the sample size is large enough."
            if normality_status == "PASS"
            else "Differences do not pass the Anderson-Darling normality check at α = 0.05."
        )
    else:
        normality_status = "WARNING"
        normality_message = "Too few distinct paired differences to assess normality reliably."

    outlier_positions = (np.flatnonzero(outlier_mask) + 1).tolist()
    outlier_count = len(outlier_positions)
    outlier_status = "PASS" if outlier_count == 0 else "WARNING"
    if outlier_count == 0:
        outlier_message = (
            "There are no unusual paired differences. "
            "Unusual data can have a strong influence on the results."
        )
    else:
        outlier_message = (
            f"{outlier_count} unusual paired difference(s) detected. "
            "Unusual data can have a strong influence on the results."
        )

    power_by_target = {
        target: _paired_ttest_detectable_difference(
            target, std_difference, sample_size
        )
        for target in (0.60, 0.70, 0.80, 0.90)
    }
    observed_power = _paired_ttest_power(
        abs(mean_difference), std_difference, sample_size
    )

    p_value = 2.0 * sp_stats.t.sf(
        abs(mean_difference / (std_difference / math.sqrt(sample_size))) if std_difference > 0 else 0.0,
        sample_size - 1,
    )
    delta_90 = power_by_target[0.90]
    if p_value >= 0.05:
        sample_size_message = (
            f"Your data does not provide sufficient evidence to conclude that the mean of {system_a_name} differs from {system_b_name}. "
            "This may result from having a sample size that is too small. "
            f"Based on your sample size, standard deviation of the paired differences, "
            f"and α, you would have a 90% chance of detecting a difference of {_format_smart(delta_90)}. "
            "To determine how large your samples need to be to detect a difference that has "
            "practical implications, repeat the analysis and enter a value for the difference."
        )
    else:
        sample_size_message = (
            f"Your data provides sufficient evidence to conclude that the mean of {system_a_name} differs from {system_b_name} (p < 0.05). "
            f"Your sample size (n = {sample_size}) is large enough to detect a difference between the means with adequate statistical power."
        )
    sample_size_status = "INFO" if p_value >= 0.05 else "PASS"

    return {
        "Normality_Status": normality_status,
        "Normality_Message": normality_message,
        "Anderson_Darling": normality_statistic,
        "Anderson_Darling_Critical": normality_critical_value,
        "Outlier_Positions": outlier_positions,
        "Outlier_Count": outlier_count,
        "Outlier_Status": outlier_status,
        "Outlier_Message": outlier_message,
        "Sample_Size_Status": sample_size_status,
        "Sample_Size_Message": sample_size_message,
        "Sample_Size_N": sample_size,
        "Observed_Power": observed_power,
        "Detectable_Differences": power_by_target,
        "Alpha": 0.05,
    }


def _paired_ttest_power(
    difference: float,
    std_difference: float,
    sample_size: int,
    alpha: float = 0.05,
) -> float:
    """Calculate two-sided paired t-test power for a mean difference."""
    if std_difference <= 0:
        return 1.0 if difference > 0 else alpha
    degrees_of_freedom = sample_size - 1
    critical_value = sp_stats.t.ppf(1 - alpha / 2, degrees_of_freedom)
    noncentrality = difference * math.sqrt(sample_size) / std_difference
    return float(
        sp_stats.norm.cdf(-critical_value - noncentrality)
        + sp_stats.norm.sf(critical_value - noncentrality)
    )


def _paired_ttest_detectable_difference(
    target_power: float,
    std_difference: float,
    sample_size: int,
) -> float:
    """Find the positive mean difference detectable at a target power."""
    if std_difference <= 0:
        return 0.0
    upper_bound = std_difference * 10 / math.sqrt(sample_size)
    return float(
        brentq(
            lambda difference: _paired_ttest_power(
                difference, std_difference, sample_size
            ) - target_power,
            0.0,
            upper_bound,
        )
    )


def _format_smart(value: float) -> str:
    """Format a numeric value matching Minitab's compact scientific style."""
    if value == 0:
        return "0"
    magnitude = abs(value)
    if magnitude >= 100000 or (magnitude < 0.0001 and magnitude > 0):
        return f"{value:.4E}"
    if magnitude < 1 and magnitude > 0:
        return f"{value:.8f}".rstrip("0").rstrip(".")
    return f"{value:.6g}"


def build_minitab_summary_comments(
    metrics: dict[str, object],
) -> list[dict[str, str]]:
    """Return the three structured Minitab-style comment blocks."""
    p_value = float(metrics["P_Value"])
    mean_d = float(metrics["Mean_D"])
    ci_lower = float(metrics["CI_Lower"])
    ci_upper = float(metrics["CI_Upper"])
    alpha = 0.05
    if p_value < alpha:
        test_comment = (
            "Test: There is sufficient evidence to conclude that the means "
            f"Differ at the {alpha:.2f} level of significance."
        )
    else:
        test_comment = (
            "Test: There is not enough evidence to conclude that the means "
            f"Differ at the {alpha:.2f} level of significance."
        )
    ci_comment = (
        f"CI: Quantifies the uncertainty associated with estimating the mean "
        f"Difference from sample data. You can be 95% confident that the true "
        f"mean difference is between {_format_smart(ci_lower)} and {_format_smart(ci_upper)}."
    )
    distribution_comment = (
        "Distribution of Differences: Compare the location of the differences to zero. "
        "Look for unusual differences before interpreting the results of the test."
    )
    return [
        {"heading": "Test", "body": test_comment},
        {"heading": "CI", "body": ci_comment},
        {"heading": "Distribution of Differences", "body": distribution_comment},
    ]


def build_report_card_rows(
    metrics: dict[str, object],
    diagnostics: dict[str, object],
) -> list[dict[str, str]]:
    """Return three rows (Unusual Data, Normality, Sample Size) for the report card table."""
    outlier_icon = "✅" if diagnostics["Outlier_Status"] == "PASS" else "⚠️"
    outlier_check = "Unusual Data"
    normality_icon = "✅" if diagnostics["Normality_Status"] == "PASS" else "⚠️"
    normality_check = "Normality"
    sample_size_check = "Sample Size"
    if diagnostics["Sample_Size_Status"] == "PASS":
        sample_size_icon = "✅"
    elif diagnostics["Sample_Size_Status"] == "INFO":
        sample_size_icon = "ⓘ"
    else:
        sample_size_icon = "⚠️"
    return [
        {"Check": outlier_check, "Icon": outlier_icon, "Description": str(diagnostics["Outlier_Message"])},
        {"Check": normality_check, "Icon": normality_icon, "Description": str(diagnostics["Normality_Message"])},
        {"Check": sample_size_check, "Icon": sample_size_icon, "Description": str(diagnostics["Sample_Size_Message"])},
    ]


def build_power_explanatory_text(
    diagnostics: dict[str, object],
) -> dict[str, str]:
    """Return paragraph + footer text explaining the power analysis (Minitab style)."""
    alpha = float(diagnostics.get("Alpha", 0.05))
    sample_size = int(diagnostics.get("Sample_Size_N", 0))
    detectable = diagnostics["Detectable_Differences"]
    delta_60 = float(detectable[0.60])
    delta_90 = float(detectable[0.90])
    paragraph = (
        f"For α = {alpha:.2f} and sample size = {sample_size}: "
        f"If the true means differed by {_format_smart(delta_60)}, you would have a 60% chance of "
        f"detecting the difference with a paired test. If they differed by {_format_smart(delta_90)}, "
        f"you would have a 90% chance."
    )
    footer = (
        "Power is a function of the sample size and the standard deviation. "
        "To detect smaller differences, consider increasing the sample size."
    )
    return {"paragraph": paragraph, "footer": footer}


# ---------------------------------------------------------------------------
# Chart Rendering
# ---------------------------------------------------------------------------

def _render_histogram_differences(
    differences: list[float],
) -> str:
    """Render histogram of differences with a vertical line at zero.

    Args:
        differences: List of difference values (A - B).

    Returns:
        Base-64 encoded PNG string.
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("#FEFEFE")

    CLR_BAR = "#B0B0BA"
    CLR_REF = "#1A8754"
    CLR_CARD = "#FFFFFF"
    CLR_SPINE = "#D1D1D6"
    CLR_LABEL = "#5A5A66"
    CLR_TITLE = "#010101"

    n_bins = min(12, max(5, int(np.sqrt(len(differences)))))
    ax.hist(
        differences,
        bins=n_bins,
        color=CLR_BAR,
        edgecolor=CLR_CARD,
        lw=0.6,
        rwidth=0.85,
        alpha=0.85,
    )
    ax.axvline(x=0, color=CLR_REF, ls="-", lw=2.5, alpha=0.9, label="Zero (No Difference)")

    ax.set_facecolor(CLR_CARD)
    ax.set_xlabel("Difference (System A − System B)", fontsize=10, color=CLR_LABEL)
    ax.set_ylabel("Frequency", fontsize=10, color=CLR_LABEL)
    ax.set_title("Histogram of Paired Differences", fontsize=12, fontweight="bold", color=CLR_TITLE, pad=10)
    ax.tick_params(labelsize=9, colors=CLR_LABEL)
    ax.grid(True, alpha=0.4, color="#E0E0E4", axis="y")
    for spine in ax.spines.values():
        spine.set_color(CLR_SPINE)
    ax.legend(fontsize=9, loc="best", facecolor=CLR_CARD, edgecolor=CLR_SPINE, labelcolor=CLR_LABEL)

    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor="#FEFEFE")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _render_individual_value_plot(
    system_a: list[float],
    system_b: list[float],
) -> str:
    """Render scatter plot of System A vs System B with Y=X identity line.

    Args:
        system_a: System A measurements.
        system_b: System B measurements.

    Returns:
        Base-64 encoded PNG string.
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor("#FEFEFE")

    CLR_POINT_FILL = "#FF6135"
    CLR_POINT_EDGE = "#1A8754"
    CLR_IDENTITY = "#3A3A44"
    CLR_CARD = "#FFFFFF"
    CLR_SPINE = "#D1D1D6"
    CLR_LABEL = "#5A5A66"
    CLR_TITLE = "#010101"

    a_arr = np.array(system_a, dtype=float)
    b_arr = np.array(system_b, dtype=float)

    ax.scatter(
        a_arr,
        b_arr,
        s=80,
        alpha=0.9,
        facecolors=CLR_POINT_FILL,
        edgecolors=CLR_POINT_EDGE,
        linewidth=1.0,
        label="Paired Observations",
    )

    # Y=X identity line
    min_val = min(a_arr.min(), b_arr.min())
    max_val = max(a_arr.max(), b_arr.max())
    range_val = max_val - min_val
    extend = range_val * 0.05
    line_pts = [min_val - extend, max_val + extend]
    ax.plot(line_pts, line_pts, color=CLR_IDENTITY, ls="--", lw=2, alpha=0.9, label="Identity (A=B)")

    ax.set_facecolor(CLR_CARD)
    ax.set_xlabel("System A", fontsize=11, color=CLR_LABEL, fontweight="bold")
    ax.set_ylabel("System B", fontsize=11, color=CLR_LABEL, fontweight="bold")
    ax.set_title("Individual Value Plot: System A vs System B", fontsize=12, fontweight="bold", color=CLR_TITLE, pad=10)
    ax.tick_params(labelsize=9, colors=CLR_LABEL)
    ax.grid(True, alpha=0.3, color="#E0E0E4")
    for spine in ax.spines.values():
        spine.set_color(CLR_SPINE)
    ax.legend(fontsize=10, loc="best", facecolor=CLR_CARD, edgecolor=CLR_SPINE, labelcolor=CLR_LABEL)

    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor="#FEFEFE")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _render_boxplot_differences(
    differences: list[float],
) -> str:
    """Render boxplot of differences.

    Args:
        differences: List of difference values.

    Returns:
        Base-64 encoded PNG string.
    """
    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor("#FEFEFE")

    CLR_BOX = "#B0B0BA"
    CLR_CARD = "#FFFFFF"
    CLR_SPINE = "#D1D1D6"
    CLR_LABEL = "#5A5A66"
    CLR_TITLE = "#010101"
    CLR_MEDIAN = "#FF420D"

    bp = ax.boxplot(
        differences,
        vert=True,
        patch_artist=True,
        widths=0.5,
        showmeans=True,
        meanline=False,
    )

    # Customize box colors
    for patch in bp["boxes"]:
        patch.set_facecolor(CLR_BOX)
        patch.set_alpha(0.7)
        patch.set_edgecolor("#3A3A44")
        patch.set_linewidth(1.2)

    for whisker in bp["whiskers"]:
        whisker.set_color("#3A3A44")
        whisker.set_linewidth(1.2)

    for cap in bp["caps"]:
        cap.set_color("#3A3A44")
        cap.set_linewidth(1.2)

    for median in bp["medians"]:
        median.set_color(CLR_MEDIAN)
        median.set_linewidth(2)

    # Mean marker
    for mean in bp["means"]:
        mean.set_marker("o")
        mean.set_markerfacecolor("#1A8754")
        mean.set_markeredgecolor("#010101")
        mean.set_markersize(7)

    ax.axhline(y=0, color="#1A8754", ls="-", lw=2, alpha=0.6, label="Zero")

    ax.set_facecolor(CLR_CARD)
    ax.set_ylabel("Difference (System A − System B)", fontsize=11, color=CLR_LABEL, fontweight="bold")
    ax.set_title("Boxplot of Paired Differences", fontsize=12, fontweight="bold", color=CLR_TITLE, pad=10)
    ax.set_xticklabels(["Differences"])
    ax.tick_params(labelsize=9, colors=CLR_LABEL)
    ax.grid(True, alpha=0.3, color="#E0E0E4", axis="y")
    for spine in ax.spines.values():
        spine.set_color(CLR_SPINE)

    custom_lines = [
        plt.Line2D([0], [0], color=CLR_MEDIAN, lw=2),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#1A8754", markersize=7, markeredgecolor="#010101"),
    ]
    ax.legend(custom_lines, ["Median", "Mean"], fontsize=9, loc="best", facecolor=CLR_CARD, edgecolor=CLR_SPINE, labelcolor=CLR_LABEL)

    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor="#FEFEFE")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _render_stats_table_chart(
    metrics: dict[str, object],
) -> str:
    """Render a summary statistics table as a chart-like image.

    This creates a visual representation of the stats table for consistency
    with the chart-embedded approach in the dashboard.

    Args:
        metrics: Dictionary from calculate_paired_ttest_metrics.

    Returns:
        Base-64 encoded PNG string.
    """
    fig, ax = plt.subplots(figsize=(9, 4))
    fig.patch.set_facecolor("#FEFEFE")
    ax.axis("off")

    # Build table data
    table_data = [
        ["Statistic", "System A", "System B", "Difference"],
        [
            "N",
            f"{int(metrics['N'])}",
            f"{int(metrics['N'])}",
            f"{int(metrics['N'])}",
        ],
        [
            "Mean",
            f"{float(metrics['Mean_A']):.6f}",
            f"{float(metrics['Mean_B']):.6f}",
            f"{float(metrics['Mean_D']):.6f}",
        ],
        [
            "StDev",
            f"{float(metrics['StDev_A']):.6f}",
            f"{float(metrics['StDev_B']):.6f}",
            f"{float(metrics['StDev_D']):.6f}",
        ],
        [
            "SE Mean",
            f"{float(metrics['SE_A']):.6f}",
            f"{float(metrics['SE_B']):.6f}",
            f"{float(metrics['SE_D']):.6f}",
        ],
    ]

    table = ax.table(
        cellText=table_data,
        cellLoc="center",
        loc="center",
        colWidths=[0.25, 0.25, 0.25, 0.25],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2.5)

    # Style header row
    for i in range(4):
        table[(0, i)].set_facecolor("#3A3A44")
        table[(0, i)].set_text_props(weight="bold", color="white")

    # Style data rows
    for i in range(1, len(table_data)):
        for j in range(4):
            if i % 2 == 0:
                table[(i, j)].set_facecolor("#F5F5F5")
            else:
                table[(i, j)].set_facecolor("#FFFFFF")
            table[(i, j)].set_edgecolor("#D1D1D6")

    plt.title("Summary Statistics", fontsize=13, fontweight="bold", pad=15, color="#010101")
    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor="#FEFEFE")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# Dashboard Generation
# ---------------------------------------------------------------------------

def create_paired_ttest_dashboard(
    paired_df: pd.DataFrame,
    metrics: dict[str, object],
    output_path: Path | None = None,
    system_a_name: str = "System A",
    system_b_name: str = "System B",
) -> str:
    """Generate a self-contained Minitab Assistant-style Paired T-Test report.

    The exported report mirrors the interactive Summary Report, Diagnostic
    Report, and Report Card views with exactly seven embedded figures that
    match the visual style of the Minitab Assistant screenshots.
    """
    from html import escape

    from .paired_visualization import (
        create_histogram_ci_figure,
        create_power_figure,
        create_paired_slopegraph_figure,
        create_pvalue_gauge_figure,
        create_run_chart_figure,
        create_stats_tables_figure,
        create_worksheet_order_figure,
    )
    from .presentation import (
        format_paired_preview,
        paired_data_quality_summary,
        paired_outliers_dataframe,
    )

    def encode_figure(figure: plt.Figure) -> str:
        buffer = BytesIO()
        figure.savefig(buffer, format="png", dpi=150, bbox_inches="tight", facecolor="#FFFFFF")
        plt.close(figure)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    diagnostics = calculate_paired_ttest_diagnostics(
        paired_df["System_A"].tolist(),
        paired_df["System_B"].tolist(),
        system_a_name=system_a_name,
        system_b_name=system_b_name,
    )
    outlier_positions: list[int] = list(diagnostics["Outlier_Positions"])

    gauge_figure = create_pvalue_gauge_figure(metrics, system_a_name=system_a_name, system_b_name=system_b_name)
    stats_tables_figure = create_stats_tables_figure(metrics, system_a_name=system_a_name, system_b_name=system_b_name)
    histogram_ci_figure = create_histogram_ci_figure(paired_df, metrics)
    worksheet_figure = create_worksheet_order_figure(
        paired_df, outlier_positions, system_a_name=system_a_name, system_b_name=system_b_name
    )
    slopegraph_figure = create_paired_slopegraph_figure(
        paired_df, metrics, system_a_name=system_a_name, system_b_name=system_b_name
    )
    run_figure = create_run_chart_figure(paired_df, metrics)
    power_figure = create_power_figure(diagnostics, metrics)

    images = {
        "gauge": encode_figure(gauge_figure),
        "stats_tables": encode_figure(stats_tables_figure),
        "histogram_ci": encode_figure(histogram_ci_figure),
        "worksheet": encode_figure(worksheet_figure),
        "pairs": encode_figure(slopegraph_figure),
        "run": encode_figure(run_figure),
        "power": encode_figure(power_figure),
    }

    comments = build_minitab_summary_comments(metrics)
    comments_html = "<ul>" + "".join(
        f"<li style='margin:6px 0;'><strong>{escape(c['heading'])}:</strong> {escape(c['body'].replace(c['heading'] + ': ', '').replace(c['heading'] + ' ', '')) if c['body'].startswith(c['heading']) else escape(c['body'])}</li>"
        for c in comments
    ) + "</ul>"

    report_rows = build_report_card_rows(metrics, diagnostics)
    report_card_html = (
        "<table class='report-table' style='width:100%;border-collapse:collapse;font-size:14px;'>"
        "<thead><tr style='background:#E8E8E8;'>"
        "<th style='padding:10px;text-align:left;border:1px solid #BBB;'>Check</th>"
        "<th style='padding:10px;text-align:center;border:1px solid #BBB;'>Status</th>"
        "<th style='padding:10px;text-align:left;border:1px solid #BBB;'>Description</th>"
        "</tr></thead><tbody>"
        + "".join(
            f"<tr>"
            f"<td style='padding:10px;border:1px solid #BBB;font-weight:600;'>{escape(r['Check'])}</td>"
            f"<td style='padding:10px;border:1px solid #BBB;text-align:center;font-size:22px;'>{escape(r['Icon'])}</td>"
            f"<td style='padding:10px;border:1px solid #BBB;line-height:1.55;'>{escape(r['Description'])}</td>"
            f"</tr>"
            for r in report_rows
        )
        + "</tbody></table>"
    )

    power_text = build_power_explanatory_text(diagnostics)

    preview_html = format_paired_preview(paired_df).to_html(index=False, classes="data-table", border=0)
    quality_html = paired_data_quality_summary(paired_df).to_html(classes="data-table", border=0)
    outlier_data_html = paired_outliers_dataframe(
        paired_df, diagnostics["Outlier_Positions"]
    ).to_html(index=False, classes="data-table", border=0)
    outlier_section_body = (
        "<p class='pass'>No severe outliers detected (&gt; 3σ).</p>"
        if not diagnostics["Outlier_Count"]
        else f"<p class='warning'>{int(diagnostics['Outlier_Count'])} severe outlier(s) detected (&gt; 3σ).</p>{outlier_data_html}"
    )

    html_content = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Paired t Test Report</title><style>
:root {{ --bg:#F1F1F1; --surface:#FFFFFF; --raised:#E8E8E8; --text:#202020; --muted:#5D5D5D; --border:#C9C9C9; --accent:#E8801C; --green:#1A6B3C; --red:#B22222; --yellow:#8A5A00; --blue:#0F4C8C; }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--bg); color:var(--text); font:14px "Segoe UI",sans-serif; line-height:1.55; }}
.page {{ max-width:1440px; margin:auto; padding:28px; }} .header {{ border-bottom:2px solid var(--border); margin-bottom:20px; padding-bottom:16px; text-align:center; }}
h1 {{ margin:0; font-size:24px; color:#333; }} h2 {{ font-size:16px; margin:0 0 14px; color:#333; }} h3 {{ font-size:14px; margin:0 0 8px; }} .subtitle {{ color:var(--muted); font-size:14px; margin-top:4px; }} .muted {{ color:var(--muted); }}
.grid2 {{ display:grid; gap:16px; grid-template-columns:repeat(2,minmax(0,1fr)); }}
.card {{ background:var(--surface); border:1px solid var(--border); border-radius:6px; padding:16px; margin-bottom:16px; }}
.tabs {{ display:flex; gap:4px; border-bottom:1px solid var(--border); margin:22px 0 16px; }} .tab {{ border:0; border-radius:6px 6px 0 0; background:var(--raised); color:var(--text); cursor:pointer; font-weight:600; padding:10px 16px; font-size:14px; }} .tab.active {{ background:var(--accent); color:#fff; }} .panel {{ display:none; }} .panel.active {{ display:block; }}
.chart {{ width:100%; height:auto; display:block; }} .data-table {{ width:100%; border-collapse:collapse; font-size:13px; }} .data-table th {{ background:#444; color:#fff; text-align:left; padding:8px; }} .data-table td {{ padding:8px; border-bottom:1px solid var(--border); }} .data-table tr:nth-child(even) {{ background:var(--raised); }}
.pass {{ color:var(--green); font-weight:600; }} .warning {{ color:var(--yellow); font-weight:600; }} ul {{ margin:0; padding-left:20px; }} ul li {{ padding:2px 0; }}
.footer-note {{ background:#F6F6F6; border-left:3px solid var(--accent); padding:10px 14px; font-size:13px; color:var(--muted); margin-top:8px; }}
.comments-card {{ background:#FAFAFA; border:1px solid var(--border); border-radius:6px; padding:14px 18px; }}
@media(max-width:800px) {{ .grid2 {{ grid-template-columns:1fr; }} .page {{ padding:16px; }} }}
</style></head><body><main class="page">
<header class="header">
  <h1>Paired t Test for the Mean of {escape(system_a_name)} and {escape(system_b_name)}</h1>
  <div class="subtitle">Two-sided paired t-test · α = 0.05</div>
</header>
<nav class="tabs"><button class="tab active" data-tab="summary">Summary Report</button><button class="tab" data-tab="diagnostic">Diagnostic Report</button><button class="tab" data-tab="card">Report Card</button></nav>

<section id="summary" class="panel active">
  <div class="grid2">
    <article class="card"><img class="chart" src="data:image/png;base64,{images['gauge']}" alt="Do the means differ?"></article>
    <article class="card"><img class="chart" src="data:image/png;base64,{images['stats_tables']}" alt="Statistics tables: Paired Differences and Individual Samples"></article>
    <article class="card"><img class="chart" src="data:image/png;base64,{images['histogram_ci']}" alt="Distribution of the Differences with CI I-bar"></article>
    <article class="card comments-card">
      <h2>Comments</h2>
      {comments_html}
    </article>
  </div>
</section>

<section id="diagnostic" class="panel">
  <article class="card"><img class="chart" src="data:image/png;base64,{images['worksheet']}" alt="Paired data in worksheet order"></article>
  <div class="grid2">
    <article class="card"><img class="chart" src="data:image/png;base64,{images['pairs']}" alt="Paired measurements comparison"></article>
    <article class="card"><img class="chart" src="data:image/png;base64,{images['run']}" alt="Differences by observation order"></article>
  </div>
  <article class="card"><img class="chart" src="data:image/png;base64,{images['power']}" alt="Power and detectable difference analysis"></article>
  <article class="card">
    <p class="muted">{escape(power_text['paragraph'])}</p>
    <div class="footer-note">{escape(power_text['footer'])}</div>
  </article>
  <article class="card">
    <h2>Severe outlier summary (&gt; 3σ)</h2>
    {outlier_section_body}
  </article>
</section>

<section id="card" class="panel">
  <h1 style="font-size:20px;margin-bottom:18px;">Report Card</h1>
  <article class="card" style="overflow-x:auto;">
    {report_card_html}
  </article>
  <div class="grid2">
    <article class="card"><h2>Uploaded paired data</h2>{preview_html}</article>
    <article class="card"><h2>Input quality</h2>{quality_html}</article>
  </div>
</section>
</main>
<script>document.querySelectorAll('.tab').forEach(button=>button.addEventListener('click',()=>{{
  document.querySelectorAll('.tab,.panel').forEach(item=>item.classList.remove('active'));
  button.classList.add('active');
  document.getElementById(button.dataset.tab).classList.add('active');
}}));</script></body></html>"""
    if output_path is not None:
        output_path.write_text(html_content, encoding="utf-8")
        print(f"Dashboard created: {output_path}")
    return html_content
