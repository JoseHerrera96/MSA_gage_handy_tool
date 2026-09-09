"""Matplotlib figures used by the interactive Paired T-Test reports.

All figures match the Minitab Assistant visual style for paired t-tests:
- Horizontal 3-zone p-value decision indicator with orange needle and boxed P-value
- Two stacked statistics tables (Paired Differences + Individual Samples)
- Distribution of Differences histogram with top-mounted red 95% CI I-bar and green zero line
- Worksheet-order paired data scatter with connecting pair lines, grand mean, and red outlier highlights
- Segmented power gauge with detectable-difference table
- Differences by observation order run chart and paired slopegraph
"""

from __future__ import annotations

import math
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Styling constants matching Minitab Assistant
# ---------------------------------------------------------------------------
_DARK = "#202020"
_MUTED = "#555555"
_GRID = "#E2E2E6"
_BG = "#FFFFFF"
_AXIS_BG = "#FFFFFF"
_SPINE = "#BBBBBB"

_MINITAB_BLUE = "#6B9AC9"
_MINITAB_BLUE_DARK = "#0F4C8C"
_MINITAB_BLUE_LIGHT = "#8EAECF"
_MINITAB_BLUE_PALE = "#D4E1EE"
_MINITAB_GREEN = "#1A6B3C"
_MINITAB_RED = "#B22222"
_MINITAB_ORANGE = "#E8801C"
_MINITAB_YELLOW = "#F1C240"

_TITLE_WEIGHT = "bold"
_TITLE_SIZE = 12
_SUBTITLE_SIZE = 9


def _format_smart(value: float) -> str:
    """Format numeric values cleanly, matching Minitab's compact scientific style."""
    if value == 0:
        return "0"
    mag = abs(value)
    if mag >= 100000 or (0 < mag < 0.0001):
        # Format as e.g. -6.6667E-06 or 4.19E-05
        formatted = f"{value:.4E}"
        parts = formatted.split("E")
        coef = parts[0].rstrip("0").rstrip(".")
        return f"{coef}E{parts[1]}"
    if 0 < mag < 1:
        return f"{value:.6g}"
    return f"{value:.5g}"


def _style_axis(axis: plt.Axes) -> None:
    axis.set_facecolor(_AXIS_BG)
    axis.grid(True, color=_GRID, alpha=0.8, zorder=0, lw=0.8)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axis.spines[side].set_color(_SPINE)
        axis.spines[side].set_linewidth(0.8)
    axis.tick_params(labelsize=8.5, colors=_DARK, width=0.8)


# ---------------------------------------------------------------------------
# 1. P-value Decision Indicator (Horizontal Bar)
# ---------------------------------------------------------------------------

def create_pvalue_gauge_figure(
    metrics: dict[str, Any],
    system_a_name: str = "System A",
    system_b_name: str = "System B",
) -> plt.Figure:
    """Minitab-style horizontal "Do the means differ?" decision bar."""
    p_value = float(metrics["P_Value"])
    alpha = 0.05

    fig, axis = plt.subplots(figsize=(9.2, 2.9))
    fig.patch.set_facecolor(_BG)
    axis.set_facecolor(_BG)
    axis.set_xlim(-0.02, 1.02)
    axis.set_ylim(0, 1.0)

    # Scale mapping:
    # 0 maps to 0.08
    # 0.05 maps to 0.22 (alpha boundary)
    # 0.1 maps to 0.36
    # 0.5 maps to 0.90
    # > 0.5 maps to 0.94
    x_0 = 0.08
    x_alpha = 0.22
    x_01 = 0.36
    x_05 = 0.90
    x_end = 0.95

    # Top scale header bar
    axis.add_patch(
        mpatches.Rectangle(
            (x_0, 0.69),
            x_end - x_0,
            0.12,
            facecolor="#E6E6E6",
            edgecolor="#AAAAAA",
            lw=0.8,
            zorder=2,
        )
    )

    # Ticks & labels on top header
    scale_ticks = [
        (x_0, "0"),
        (x_alpha, "0.05"),
        (x_01, "0.1"),
        (x_05, "> 0.5"),
    ]
    for x_pos, label in scale_ticks:
        axis.plot([x_pos, x_pos], [0.69, 0.81], color="#777777", lw=0.8, zorder=3)
        axis.text(x_pos, 0.835, label, ha="center", va="bottom", fontsize=8.5, color=_DARK)

    # Main bar zones (under header: y = 0.46 to 0.69)
    bar_y, bar_h = 0.46, 0.23

    # Zone 1: 0 to 0.05 (Dark Blue - "Yes")
    axis.add_patch(
        mpatches.Rectangle(
            (x_0, bar_y),
            x_alpha - x_0,
            bar_h,
            facecolor=_MINITAB_BLUE_DARK,
            edgecolor="#888888",
            lw=0.6,
            zorder=2,
        )
    )
    # Zone 2: 0.05 to 0.1 (Medium-Light Blue)
    axis.add_patch(
        mpatches.Rectangle(
            (x_alpha, bar_y),
            x_01 - x_alpha,
            bar_h,
            facecolor=_MINITAB_BLUE_LIGHT,
            edgecolor="#888888",
            lw=0.6,
            zorder=2,
        )
    )
    # Zone 3: 0.1 to >0.5 (Pale Gray-Blue - "No")
    axis.add_patch(
        mpatches.Rectangle(
            (x_01, bar_y),
            x_end - x_01,
            bar_h,
            facecolor=_MINITAB_BLUE_PALE,
            edgecolor="#888888",
            lw=0.6,
            zorder=2,
        )
    )

    # Dashed guidelines down from 0.05 and 0.1
    for x_pos in (x_alpha, x_01):
        axis.plot([x_pos, x_pos], [0.40, 0.69], color="#AAAAAA", ls="--", lw=0.9, zorder=3)

    # Labels "Yes" and "No"
    axis.text(x_0 - 0.02, bar_y + bar_h / 2, "Yes", ha="right", va="center", fontsize=11, fontweight="bold", color=_DARK)
    axis.text(x_end + 0.02, bar_y + bar_h / 2, "No", ha="left", va="center", fontsize=11, fontweight="bold", color=_DARK)

    # Map actual p-value to x-coordinate
    if p_value <= 0.05:
        p_x = x_0 + (p_value / 0.05) * (x_alpha - x_0)
    elif p_value <= 0.10:
        p_x = x_alpha + ((p_value - 0.05) / 0.05) * (x_01 - x_alpha)
    elif p_value <= 0.50:
        p_x = x_01 + ((p_value - 0.10) / 0.40) * (x_05 - x_01)
    else:
        p_x = x_05 + min((p_value - 0.50) / 0.50, 1.0) * (x_end - x_05)
    p_x = max(x_0, min(x_end, p_x))

    # Orange vertical needle
    axis.plot([p_x, p_x], [0.42, 0.82], color=_MINITAB_ORANGE, lw=2.8, zorder=6)

    # Boxed P-value label below the needle
    box_x = min(max(p_x, x_0 + 0.05), x_end - 0.05)
    axis.text(
        box_x,
        0.34,
        f"P = {p_value:.3f}",
        ha="center",
        va="top",
        fontsize=9.5,
        color=_MINITAB_ORANGE,
        fontweight="bold",
        bbox=dict(boxstyle="square,pad=0.25", fc="#FFFFFF", ec=_MINITAB_ORANGE, lw=1.3),
        zorder=7,
    )

    # Title
    axis.set_title(
        "Do the means differ?",
        fontsize=_TITLE_SIZE,
        fontweight=_TITLE_WEIGHT,
        color=_DARK,
        pad=10,
    )

    # Dynamic conclusion sentence below
    if p_value < alpha:
        conclusion_text = (
            f"The mean of {system_a_name} is significantly different from the mean of {system_b_name} (p < 0.05)."
        )
    else:
        conclusion_text = (
            f"The mean of {system_a_name} is not significantly different from the mean of {system_b_name} (p > 0.05)."
        )

    axis.text(
        0.01,
        0.08,
        conclusion_text,
        ha="left",
        va="bottom",
        fontsize=9.2,
        color=_DARK,
    )

    axis.axis("off")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 2. Distribution of Differences Histogram with inline 95% CI
# ---------------------------------------------------------------------------

def create_histogram_ci_figure(
    paired_df: pd.DataFrame,
    metrics: dict[str, Any],
) -> plt.Figure:
    """Distribution of the Differences histogram with top-mounted 95% CI I-bar."""
    differences = paired_df["Difference"].to_numpy(dtype=float)
    mean_d = float(metrics["Mean_D"])
    ci_lower = float(metrics["CI_Lower"])
    ci_upper = float(metrics["CI_Upper"])

    fig, axis = plt.subplots(figsize=(8.8, 5.6))
    fig.patch.set_facecolor(_BG)

    n_bins = min(12, max(5, int(np.sqrt(len(differences)))))
    counts, bin_edges, patches = axis.hist(
        differences,
        bins=n_bins,
        color=_MINITAB_BLUE,
        edgecolor="#333333",
        lw=0.7,
        zorder=3,
        alpha=0.92,
        rwidth=0.96,
    )

    max_count = float(np.max(counts)) if len(counts) > 0 else 1.0
    y_top = max_count * 1.35
    axis.set_ylim(0, y_top)

    # Green dashed zero line
    axis.axvline(0, color=_MINITAB_GREEN, ls="--", lw=1.6, zorder=4)
    axis.text(0, max_count * 1.25, "0", ha="center", va="bottom", fontsize=10, color=_MINITAB_GREEN, fontweight="bold")

    # 95% CI I-bar placed at the top above the bars
    ci_y = max_count * 1.15
    cap_h = max_count * 0.06

    # Horizontal CI bar
    axis.hlines(y=ci_y, xmin=ci_lower, xmax=ci_upper, color=_MINITAB_RED, lw=2.8, zorder=5)
    # Vertical crossbars at CI limits
    axis.vlines(x=ci_lower, ymin=ci_y - cap_h, ymax=ci_y + cap_h, color=_MINITAB_RED, lw=2.2, zorder=5)
    axis.vlines(x=ci_upper, ymin=ci_y - cap_h, ymax=ci_y + cap_h, color=_MINITAB_RED, lw=2.2, zorder=5)
    # Circle at mean difference
    axis.plot([mean_d], [ci_y], "o", color=_DARK, markerfacecolor=_MINITAB_RED, markeredgecolor=_DARK, markersize=7, zorder=6)

    axis.set_xlabel("Difference (System A − System B)", fontsize=9.5, color=_DARK)
    axis.set_ylabel("Frequency", fontsize=9.5, color=_DARK)
    _style_axis(axis)

    axis.set_title(
        "Distribution of the Differences",
        fontsize=_TITLE_SIZE,
        fontweight=_TITLE_WEIGHT,
        color=_DARK,
        pad=18,
    )
    axis.text(
        0.5,
        1.015,
        "Where are the differences relative to zero?",
        transform=axis.transAxes,
        ha="center",
        va="bottom",
        fontsize=_SUBTITLE_SIZE,
        color=_MUTED,
    )
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 3. Paired Data in Worksheet Order
# ---------------------------------------------------------------------------

def create_worksheet_order_figure(
    paired_df: pd.DataFrame,
    outlier_positions: list[int] | None = None,
    system_a_name: str = "System A",
    system_b_name: str = "System B",
) -> plt.Figure:
    """Paired Data in Worksheet Order with pair-connecting lines and red outlier markers."""
    if outlier_positions is None:
        outlier_positions = []

    observations = paired_df["Observation"].to_numpy(dtype=float)
    system_a = paired_df["System_A"].to_numpy(dtype=float)
    system_b = paired_df["System_B"].to_numpy(dtype=float)
    grand_mean = float(np.mean(np.concatenate([system_a, system_b])))

    unusual_set = set(int(pos - 1) for pos in outlier_positions)

    fig, axis = plt.subplots(figsize=(12, 5.0))
    fig.patch.set_facecolor(_BG)

    # Draw vertical connecting line between each pair
    for i, (obs, val_a, val_b) in enumerate(zip(observations, system_a, system_b)):
        line_color = _MINITAB_RED if i in unusual_set else "#888888"
        line_width = 1.6 if i in unusual_set else 0.8
        axis.plot([obs, obs], [val_a, val_b], color=line_color, lw=line_width, zorder=2)

    # Plot regular observations
    reg_mask = np.array([i not in unusual_set for i in range(len(observations))], dtype=bool)
    if reg_mask.any():
        axis.scatter(
            observations[reg_mask],
            system_a[reg_mask],
            color=_DARK,
            s=34,
            marker="o",
            zorder=4,
            label=system_a_name,
        )
        axis.scatter(
            observations[reg_mask],
            system_b[reg_mask],
            color=_MINITAB_BLUE_DARK,
            s=34,
            marker="s",
            zorder=4,
            label=system_b_name,
        )

    # Plot unusual observations (flagged in red)
    if len(unusual_set) > 0:
        unusual_mask = ~reg_mask
        axis.scatter(
            observations[unusual_mask],
            system_a[unusual_mask],
            color=_MINITAB_RED,
            s=56,
            marker="o",
            edgecolors=_DARK,
            lw=0.8,
            zorder=5,
            label=f"Unusual {system_a_name}",
        )
        axis.scatter(
            observations[unusual_mask],
            system_b[unusual_mask],
            color=_MINITAB_RED,
            s=56,
            marker="s",
            edgecolors=_DARK,
            lw=0.8,
            zorder=5,
            label=f"Unusual {system_b_name}",
        )

    # Grand mean reference line
    axis.axhline(grand_mean, color="#999999", ls="--", lw=1.1, zorder=2)

    axis.set_xlabel("Observation order", fontsize=9.5, color=_DARK)
    axis.set_ylabel("Measurement", fontsize=9.5, color=_DARK)
    axis.set_title(
        "Paired Data in Worksheet Order",
        fontsize=_TITLE_SIZE,
        fontweight=_TITLE_WEIGHT,
        color=_DARK,
        pad=20,
    )
    axis.text(
        0.5,
        1.015,
        "Investigate any pairs with unusual differences (marked in red).",
        transform=axis.transAxes,
        ha="center",
        va="bottom",
        fontsize=_SUBTITLE_SIZE,
        color=_MUTED,
    )
    _style_axis(axis)

    # Deduplicate legend items
    handles, labels = axis.get_legend_handles_labels()
    seen = set()
    unique_h, unique_l = [], []
    for h, l in zip(handles, labels):
        if l not in seen:
            seen.add(l)
            unique_h.append(h)
            unique_l.append(l)
    axis.legend(unique_h, unique_l, loc="upper right", fontsize=8.5, frameon=False)

    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 4. Power and Detectable Difference Analysis
# ---------------------------------------------------------------------------

def create_power_figure(
    diagnostics: dict[str, Any],
    metrics: dict[str, Any],
) -> plt.Figure:
    """Segmented power gauge bar (left) + detectable-difference table (right)."""
    detectable = diagnostics["Detectable_Differences"]
    powers_sorted = sorted(detectable)
    sample_size = int(diagnostics.get("Sample_Size_N", 0) or metrics["N"])
    observed_diff = float(metrics["Mean_D"])
    delta_60 = float(detectable[0.60])
    delta_90 = float(detectable[0.90])

    fig, (bar_axis, table_axis) = plt.subplots(
        1, 2, figsize=(12.2, 4.6), gridspec_kw={"width_ratios": [1.0, 1.0]}
    )
    fig.patch.set_facecolor(_BG)

    # --- Left: Segmented Power Bar ---
    bar_axis.set_xlim(0, 100)
    bar_axis.set_ylim(0, 1)
    bar_axis.axis("off")
    bar_axis.set_facecolor(_BG)

    y_bottom, y_top = 0.28, 0.64

    # Outer border
    bar_axis.add_patch(
        mpatches.Rectangle(
            (0, y_bottom),
            100,
            y_top - y_bottom,
            facecolor="none",
            edgecolor="#999999",
            lw=1.0,
            zorder=4,
        )
    )

    # Color segments
    # Red: 0 to 40%
    bar_axis.add_patch(
        mpatches.Rectangle((0, y_bottom), 40, y_top - y_bottom, facecolor=_MINITAB_RED, zorder=2)
    )
    # Yellow: 40 to 90%
    bar_axis.add_patch(
        mpatches.Rectangle((40, y_bottom), 50, y_top - y_bottom, facecolor=_MINITAB_YELLOW, zorder=2)
    )
    # Green: 90 to 100%
    bar_axis.add_patch(
        mpatches.Rectangle((90, y_bottom), 10, y_top - y_bottom, facecolor=_MINITAB_GREEN, zorder=2)
    )

    # Top scale markers and labels
    top_ticks = [
        ("< 40%", 18),
        ("60%", 50),
        ("Power", 65),
        ("90%", 90),
        ("100%", 99),
    ]
    for label_text, x_pos in top_ticks:
        bar_axis.text(x_pos, y_top + 0.05, label_text, ha="center", va="bottom", fontsize=8.8, color=_DARK)
    bar_axis.plot([50, 50], [y_bottom, y_top], color="#999999", ls=":", lw=0.8, zorder=3)
    bar_axis.plot([90, 90], [y_bottom, y_top], color="#999999", ls=":", lw=0.8, zorder=3)

    # Bottom scale: deltas
    bar_axis.text(2, y_bottom - 0.08, "Difference", ha="left", va="top", fontsize=8.8, color=_DARK)
    bar_axis.text(50, y_bottom - 0.08, f"{_format_smart(delta_60)}", ha="center", va="top", fontsize=8.2, color=_DARK)
    bar_axis.text(90, y_bottom - 0.08, f"{_format_smart(delta_90)}", ha="center", va="top", fontsize=8.2, color=_DARK)

    bar_axis.set_title(
        "What is the chance of detecting a difference?",
        fontsize=_TITLE_SIZE,
        fontweight=_TITLE_WEIGHT,
        color=_DARK,
        pad=18,
    )

    # --- Right: Detectable Difference Table ---
    table_axis.set_facecolor(_BG)
    table_axis.axis("off")

    table_data = [["Difference", "Power"]]
    for p_level in powers_sorted:
        table_data.append([f"{_format_smart(detectable[p_level])}", f"{int(round(p_level * 100))}%"])

    t = table_axis.table(
        cellText=table_data[1:],
        colLabels=table_data[0],
        colWidths=[0.50, 0.35],
        cellLoc="center",
        loc="upper center",
        bbox=[0.12, 0.32, 0.80, 0.58],
    )
    t.auto_set_font_size(False)
    t.set_fontsize(9.2)
    for (row_idx, col_idx), cell in t.get_celld().items():
        cell.set_edgecolor("#BBBBBB")
        cell.set_linewidth(0.7)
        if row_idx == 0:
            cell.set_facecolor("#E8E8E8")
            cell.set_text_props(weight="bold", color=_DARK, fontsize=9.4)

    table_axis.text(
        0.5,
        0.26,
        f"Observed difference = {_format_smart(observed_diff)}",
        ha="center",
        va="top",
        fontsize=9.3,
        color=_DARK,
    )
    table_axis.set_title(
        f"What difference can you detect with a sample size of {sample_size}?",
        fontsize=_TITLE_SIZE,
        fontweight=_TITLE_WEIGHT,
        color=_DARK,
        pad=18,
    )

    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 5. Two Stacked Statistics Tables
# ---------------------------------------------------------------------------

def create_stats_tables_figure(
    metrics: dict[str, Any],
    system_a_name: str = "System A",
    system_b_name: str = "System B",
) -> plt.Figure:
    """Two stacked statistics tables: Paired Differences + Individual Samples."""
    sample_size = int(metrics["N"])
    mean_d = float(metrics["Mean_D"])
    stdev_d = float(metrics["StDev_D"])
    ci_lower = float(metrics["CI_Lower"])
    ci_upper = float(metrics["CI_Upper"])
    mean_a = float(metrics["Mean_A"])
    mean_b = float(metrics["Mean_B"])
    stdev_a = float(metrics["StDev_A"])
    stdev_b = float(metrics["StDev_B"])

    fig, (table1_ax, table2_ax) = plt.subplots(
        2, 1, figsize=(9.6, 7.0), gridspec_kw={"height_ratios": [1.0, 0.9]}
    )
    fig.patch.set_facecolor(_BG)

    # --- Table 1: Paired Differences ---
    table1_ax.set_facecolor(_BG)
    table1_ax.axis("off")
    paired_table_data = [
        ["Sample size", f"{sample_size}"],
        ["Mean", f"{_format_smart(mean_d)}"],
        ["95% CI", f"({_format_smart(ci_lower)}, {_format_smart(ci_upper)})"],
        ["Standard deviation", f"{_format_smart(stdev_d)}"],
    ]
    t1 = table1_ax.table(
        cellText=paired_table_data,
        colLabels=["Statistics", "*Paired Differences"],
        cellLoc="left",
        colWidths=[0.50, 0.46],
        loc="center",
        bbox=[0.08, 0.08, 0.88, 0.84],
    )
    t1.auto_set_font_size(False)
    t1.set_fontsize(9.5)
    t1.scale(1, 1.3)
    for (row_idx, col_idx), cell in t1.get_celld().items():
        cell.set_edgecolor("#BBBBBB")
        cell.set_linewidth(0.7)
        if row_idx == 0:
            cell.set_facecolor("#E8E8E8")
            cell.set_text_props(weight="bold", color=_DARK, fontsize=9.8)
        else:
            if col_idx == 0:
                cell.set_text_props(ha="left", x=0.04, color=_DARK)
            else:
                cell.set_text_props(ha="right", x=0.96, color=_DARK)
    table1_ax.set_title("Paired Differences", fontsize=_TITLE_SIZE, fontweight=_TITLE_WEIGHT, color=_DARK, pad=12)
    table1_ax.text(
        0.08,
        0.01,
        f"*Difference = {system_a_name} − {system_b_name}",
        transform=table1_ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.7,
        color=_MUTED,
    )

    # --- Table 2: Individual Samples ---
    table2_ax.set_facecolor(_BG)
    table2_ax.axis("off")
    sample_table_data = [
        ["Mean", f"{_format_smart(mean_a)}", f"{_format_smart(mean_b)}"],
        ["Standard deviation", f"{_format_smart(stdev_a)}", f"{_format_smart(stdev_b)}"],
    ]
    t2 = table2_ax.table(
        cellText=sample_table_data,
        colLabels=["Statistics", system_a_name, system_b_name],
        cellLoc="left",
        colWidths=[0.38, 0.30, 0.30],
        loc="center",
        bbox=[0.08, 0.16, 0.88, 0.70],
    )
    t2.auto_set_font_size(False)
    t2.set_fontsize(9.5)
    t2.scale(1, 1.4)
    for (row_idx, col_idx), cell in t2.get_celld().items():
        cell.set_edgecolor("#BBBBBB")
        cell.set_linewidth(0.7)
        if row_idx == 0:
            cell.set_facecolor("#E8E8E8")
            cell.set_text_props(weight="bold", color=_DARK, fontsize=9.8)
        else:
            if col_idx == 0:
                cell.set_text_props(ha="left", x=0.04, color=_DARK)
            else:
                cell.set_text_props(ha="right", x=0.96, color=_DARK)
    table2_ax.set_title("Individual Samples", fontsize=_TITLE_SIZE, fontweight=_TITLE_WEIGHT, color=_DARK, pad=12)

    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 6. Slopegraph and Run Chart
# ---------------------------------------------------------------------------

def create_paired_slopegraph_figure(
    paired_df: pd.DataFrame,
    metrics: dict[str, Any],
    system_a_name: str = "System A",
    system_b_name: str = "System B",
) -> plt.Figure:
    """Paired measurements as connecting lines between System A and System B."""
    system_a = paired_df["System_A"].to_numpy(dtype=float)
    system_b = paired_df["System_B"].to_numpy(dtype=float)
    differences = paired_df["Difference"].to_numpy(dtype=float)
    mean_d = float(metrics["Mean_D"])
    std_d = float(metrics["StDev_D"])

    unusual = np.zeros(len(differences), dtype=bool)
    if std_d > 0:
        unusual = np.abs(differences - mean_d) > 3 * std_d

    fig, axis = plt.subplots(figsize=(8.4, 5.2))
    fig.patch.set_facecolor(_BG)

    for i, (val_a, val_b) in enumerate(zip(system_a, system_b)):
        line_color = _MINITAB_RED if unusual[i] else "#999999"
        alpha = 1.0 if unusual[i] else 0.62
        axis.plot([0, 1], [val_a, val_b], color=line_color, alpha=alpha, lw=0.95, zorder=2)

    reg_mask = ~unusual
    axis.scatter(np.zeros(int(reg_mask.sum())), system_a[reg_mask], color=_DARK, s=28, zorder=5)
    axis.scatter(np.ones(int(reg_mask.sum())), system_b[reg_mask], color=_MINITAB_BLUE_DARK, s=28, zorder=5, marker="s")
    if unusual.any():
        axis.scatter(np.zeros(int(unusual.sum())), system_a[unusual], color=_MINITAB_RED, s=42, zorder=6, edgecolors=_DARK, lw=0.6)
        axis.scatter(np.ones(int(unusual.sum())), system_b[unusual], color=_MINITAB_RED, s=42, zorder=6, marker="s", edgecolors=_DARK, lw=0.6)

    axis.set_xlim(-0.25, 1.25)
    axis.set_xticks([0, 1])
    axis.set_xticklabels([system_a_name, system_b_name], fontsize=10, fontweight="bold")
    axis.set_ylabel("Measurement", fontsize=9.5, color=_DARK)
    axis.set_title(
        "Paired Measurements Comparison",
        fontsize=_TITLE_SIZE,
        fontweight=_TITLE_WEIGHT,
        color=_DARK,
        pad=14,
    )
    _style_axis(axis)
    fig.tight_layout()
    return fig


def create_run_chart_figure(
    paired_df: pd.DataFrame,
    metrics: dict[str, Any],
) -> plt.Figure:
    """Differences plotted in observation order with reference lines."""
    observations = paired_df["Observation"].to_numpy(dtype=float)
    differences = paired_df["Difference"].to_numpy(dtype=float)
    mean_d = float(metrics["Mean_D"])
    std_d = float(metrics["StDev_D"])

    unusual = np.zeros(len(differences), dtype=bool)
    if std_d > 0:
        unusual = np.abs(differences - mean_d) > 3 * std_d

    fig, axis = plt.subplots(figsize=(8.8, 5.2))
    fig.patch.set_facecolor(_BG)
    axis.plot(observations, differences, "-", color=_DARK, markersize=0, lw=1.2, zorder=3)
    regular = ~unusual
    axis.scatter(observations[regular], differences[regular], color=_MINITAB_BLUE_DARK, s=22, zorder=5)
    if unusual.any():
        axis.scatter(observations[unusual], differences[unusual], color=_MINITAB_RED, s=46, zorder=6, edgecolors=_DARK, lw=0.6)
    axis.axhline(0, color=_MINITAB_GREEN, ls="--", lw=1.3, label="No difference", zorder=2)
    axis.axhline(mean_d, color=_MINITAB_ORANGE, lw=1.8, label="Mean difference", zorder=2)
    if std_d > 0:
        axis.axhline(mean_d + 3 * std_d, color=_MINITAB_RED, ls=":", lw=1, zorder=2, alpha=0.7)
        axis.axhline(mean_d - 3 * std_d, color=_MINITAB_RED, ls=":", lw=1, zorder=2, alpha=0.7)
    axis.set_xlabel("Observation order", fontsize=9.5, color=_DARK)
    axis.set_ylabel("Difference (System A − System B)", fontsize=9.5, color=_DARK)
    axis.set_title(
        "Differences by Observation Order",
        fontsize=_TITLE_SIZE,
        fontweight=_TITLE_WEIGHT,
        color=_DARK,
        pad=14,
    )
    _style_axis(axis)
    axis.legend(loc="best", fontsize=8.5, frameon=False)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Backward Compatibility Aliases
# ---------------------------------------------------------------------------

def create_paired_summary_figures(
    metrics: dict[str, Any],
) -> tuple[plt.Figure, plt.Figure]:
    """Backward-compatible alias returning the two summary figures."""
    return create_pvalue_gauge_figure(metrics), create_stats_tables_figure(metrics)


def create_paired_diagnostic_figures(
    paired_df: pd.DataFrame,
    metrics: dict[str, Any],
) -> tuple[plt.Figure, plt.Figure, plt.Figure]:
    """Backward-compatible alias returning slopegraph, histogram+CI, run chart."""
    slopegraph = create_paired_slopegraph_figure(paired_df, metrics)
    histogram = create_histogram_ci_figure(paired_df, metrics)
    run = create_run_chart_figure(paired_df, metrics)
    return slopegraph, histogram, run
