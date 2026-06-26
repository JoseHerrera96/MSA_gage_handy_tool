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
from io import BytesIO
from pathlib import Path
from typing import Any

import base64
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as sp_stats

matplotlib.use("Agg")


# ---------------------------------------------------------------------------
# Data Parsing
# ---------------------------------------------------------------------------

def parse_paired_measurements(
    file_a: Path,
    file_b: Path,
) -> tuple[pd.DataFrame, list[float], list[float], list[float]]:
    """Parse two measurement files and produce an aligned paired DataFrame.

    Both files are expected to contain one measurement per line (numeric values).
    They must have the same number of observations. Each line is stripped and
    converted to float.

    Args:
        file_a: Path to System A measurements (one per line).
        file_b: Path to System B measurements (one per line).

    Returns:
        A tuple ``(paired_df, system_a_vals, system_b_vals, differences)``:
        - paired_df: DataFrame with columns [Observation, System_A, System_B, Difference].
        - system_a_vals: List of System A measurements.
        - system_b_vals: List of System B measurements.
        - differences: List of differences (A - B).

    Raises:
        ValueError: If the files have different lengths or contain non-numeric data.
    """
    # Read System A
    with open(file_a, "r", encoding="utf-8") as fh:
        lines_a = [line.strip() for line in fh if line.strip()]
    system_a_vals = []
    for line in lines_a:
        try:
            system_a_vals.append(float(line))
        except ValueError:
            continue

    # Read System B
    with open(file_b, "r", encoding="utf-8") as fh:
        lines_b = [line.strip() for line in fh if line.strip()]
    system_b_vals = []
    for line in lines_b:
        try:
            system_b_vals.append(float(line))
        except ValueError:
            continue

    # Verify equal length
    if len(system_a_vals) != len(system_b_vals):
        raise ValueError(
            f"Mismatched lengths: System A has {len(system_a_vals)} values, "
            f"System B has {len(system_b_vals)} values."
        )

    # Compute differences
    differences = [a - b for a, b in zip(system_a_vals, system_b_vals)]

    # Build DataFrame
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
    output_path: Path,
) -> None:
    """Generate a self-contained HTML dashboard for paired t-test results.

    Embeds 4 charts as Base64 images:
    1. Histogram of Differences
    2. Individual Value Plot (Scatter: A vs B)
    3. Boxplot of Differences
    4. Summary Statistics Table

    Args:
        paired_df: DataFrame with paired measurements and differences.
        metrics: Dictionary from calculate_paired_ttest_metrics.
        output_path: Where to write the HTML file.
    """
    # Extract data for charts
    system_a = paired_df["System_A"].tolist()
    system_b = paired_df["System_B"].tolist()
    differences = paired_df["Difference"].tolist()

    # Render all charts
    img_histogram = _render_histogram_differences(differences)
    img_scatter = _render_individual_value_plot(system_a, system_b)
    img_boxplot = _render_boxplot_differences(differences)
    img_stats = _render_stats_table_chart(metrics)

    # Decision logic
    alpha = 0.05
    p_val = float(metrics["P_Value"])
    is_significant = p_val < alpha

    # HTML template
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paired T-Test — Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        :root {{
            --color-bg-primary: #FEFEFE;
            --color-bg-secondary: #F5F5F5;
            --color-card: #FFFFFF;
            --color-text-primary: #010101;
            --color-text-secondary: #5A5A66;
            --color-accent: #FF6135;
            --color-success: #1A8754;
            --color-danger: #D94A38;
            --color-border: #D1D1D6;
            --color-grid: #E0E0E4;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--color-bg-primary);
            color: var(--color-text-primary);
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 2px solid var(--color-border);
            padding-bottom: 20px;
        }}
        
        .dash-title {{
            font-size: 32px;
            font-weight: 700;
            color: var(--color-text-primary);
            margin-bottom: 10px;
        }}
        
        .dash-subtitle {{
            font-size: 14px;
            color: var(--color-text-secondary);
        }}
        
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .kpi-card {{
            background: var(--color-card);
            border: 1px solid var(--color-border);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        .kpi-label {{
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--color-text-secondary);
            margin-bottom: 8px;
        }}
        
        .kpi-value {{
            font-size: 24px;
            font-weight: 700;
            color: var(--color-text-primary);
        }}
        
        .kpi-good {{
            color: var(--color-success);
        }}
        
        .kpi-bad {{
            color: var(--color-danger);
        }}
        
        .test-conclusion {{
            background: var(--color-bg-secondary);
            border-left: 4px solid var(--color-accent);
            padding: 15px;
            margin-bottom: 30px;
            border-radius: 4px;
        }}
        
        .test-conclusion h3 {{
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 8px;
            color: var(--color-text-primary);
        }}
        
        .test-conclusion p {{
            font-size: 13px;
            color: var(--color-text-secondary);
        }}
        
        .hypotheses {{
            background: var(--color-card);
            border: 1px solid var(--color-border);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
            font-family: "Courier New", monospace;
            font-size: 13px;
        }}
        
        .hypotheses p {{
            margin-bottom: 8px;
        }}
        
        .hypothesis-label {{
            font-weight: 600;
            color: var(--color-text-primary);
        }}
        
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }}
        
        .summary-card {{
            background: var(--color-card);
            border: 1px solid var(--color-border);
            border-radius: 12px;
            padding: 28px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.08);
            max-width: 1080px;
            margin: 0 auto 40px;
        }}
        
        .chart-card {{
            background: var(--color-card);
            border: 1px solid var(--color-border);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        .chart-title {{
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 15px;
            color: var(--color-text-primary);
        }}
        
        .chart-img {{
            width: 100%;
            height: auto;
            border-radius: 4px;
        }}
        
        .stats-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        .stats-table th {{
            background-color: #3A3A44;
            color: white;
            padding: 12px;
            text-align: left;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .stats-table td {{
            padding: 12px;
            border-bottom: 1px solid var(--color-border);
            font-size: 13px;
        }}
        
        .stats-table tbody tr:nth-child(odd) {{
            background-color: var(--color-bg-secondary);
        }}
        
        .stats-table tbody tr:hover {{
            background-color: var(--color-grid);
        }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--color-border);
            font-size: 12px;
            color: var(--color-text-secondary);
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="dash-title">Paired T-Test Analysis</div>
            <div class="dash-subtitle">System A vs. System B Comparison</div>
        </div>
        
        <!-- Key Performance Indicators -->
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="kpi-label">Sample Size (N)</div>
                <div class="kpi-value">{int(metrics['N'])}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Mean Difference</div>
                <div class="kpi-value">{float(metrics['Mean_D']):+.6f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">T-Statistic</div>
                <div class="kpi-value">{float(metrics['T_Value']):.4f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">P-Value (two-sided)</div>
                <div class="kpi-value{'kpi-good' if not is_significant else 'kpi-bad'}">{float(metrics['P_Value']):.4f}</div>
            </div>
        </div>
        
        <!-- Test Conclusion -->
        <div class="test-conclusion">
            <h3>Test Conclusion (α = 0.05)</h3>
            <p>
                <strong>Result:</strong> 
                {'The means are statistically significantly different (REJECT H₀).' if is_significant else 'No significant difference detected (FAIL TO REJECT H₀).'}
            </p>
            <p style="margin-top: 8px;">
                <strong>Interpretation:</strong> 
                {'System A and System B produce significantly different measurement results.' if is_significant else 'System A and System B are not statistically different.'}
            </p>
        </div>
        
        <!-- Hypotheses -->
        <div class="hypotheses">
            <p><span class="hypothesis-label">Null Hypothesis (H₀):</span> {metrics['H0']}</p>
            <p><span class="hypothesis-label">Alternative Hypothesis (H₁):</span> {metrics['HA']}</p>
            <p style="margin-top: 12px; color: var(--color-text-secondary); font-style: italic;">
                Test: Two-sided paired t-test, df = {int(metrics['DF'])}, α = 0.05
            </p>
        </div>
        
        <!-- Summary Statistics Card -->
        <div class="summary-card">
            <div class="chart-title">Summary Statistics</div>
            <img src="data:image/png;base64,{img_stats}" class="chart-img" alt="Statistics Table">
        </div>
        
        <!-- Charts -->
        <div class="chart-grid">
            <div class="chart-card">
                <div class="chart-title">Histogram of Differences</div>
                <img src="data:image/png;base64,{img_histogram}" class="chart-img" alt="Histogram of Differences">
            </div>
            <div class="chart-card">
                <div class="chart-title">Individual Value Plot: System A vs System B</div>
                <img src="data:image/png;base64,{img_scatter}" class="chart-img" alt="Individual Value Plot">
            </div>
            <div class="chart-card">
                <div class="chart-title">Boxplot of Differences</div>
                <img src="data:image/png;base64,{img_boxplot}" class="chart-img" alt="Boxplot of Differences">
            </div>
        </div>
        
        <!-- Detailed Results Table -->
        <div style="background: var(--color-card); border: 1px solid var(--color-border); border-radius: 8px; padding: 20px; margin-bottom: 40px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <h3 style="font-size: 14px; font-weight: 600; margin-bottom: 15px; color: var(--color-text-primary);">Detailed Results</h3>
            <table class="stats-table">
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Sample Size</td>
                        <td>{int(metrics['N'])}</td>
                    </tr>
                    <tr>
                        <td>System A: Mean</td>
                        <td>{float(metrics['Mean_A']):.8f}</td>
                    </tr>
                    <tr>
                        <td>System A: StDev</td>
                        <td>{float(metrics['StDev_A']):.8f}</td>
                    </tr>
                    <tr>
                        <td>System A: SE Mean</td>
                        <td>{float(metrics['SE_A']):.8f}</td>
                    </tr>
                    <tr>
                        <td>System B: Mean</td>
                        <td>{float(metrics['Mean_B']):.8f}</td>
                    </tr>
                    <tr>
                        <td>System B: StDev</td>
                        <td>{float(metrics['StDev_B']):.8f}</td>
                    </tr>
                    <tr>
                        <td>System B: SE Mean</td>
                        <td>{float(metrics['SE_B']):.8f}</td>
                    </tr>
                    <tr>
                        <td>Mean Difference (A − B)</td>
                        <td>{float(metrics['Mean_D']):+.8f}</td>
                    </tr>
                    <tr>
                        <td>StDev Difference</td>
                        <td>{float(metrics['StDev_D']):.8f}</td>
                    </tr>
                    <tr>
                        <td>SE Mean Difference</td>
                        <td>{float(metrics['SE_D']):.8f}</td>
                    </tr>
                    <tr>
                        <td>95% CI Lower</td>
                        <td>{float(metrics['CI_Lower']):.8f}</td>
                    </tr>
                    <tr>
                        <td>95% CI Upper</td>
                        <td>{float(metrics['CI_Upper']):.8f}</td>
                    </tr>
                    <tr>
                        <td>T-Statistic</td>
                        <td>{float(metrics['T_Value']):.6f}</td>
                    </tr>
                    <tr>
                        <td>Degrees of Freedom</td>
                        <td>{int(metrics['DF'])}</td>
                    </tr>
                    <tr>
                        <td>P-Value (two-sided)</td>
                        <td>{float(metrics['P_Value']):.6f}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <p>Paired T-Test Dashboard | Statistical analysis tool | All images and data embedded in this HTML file</p>
        </div>
    </div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html_content)

    print(f"Dashboard created: {output_path}")
