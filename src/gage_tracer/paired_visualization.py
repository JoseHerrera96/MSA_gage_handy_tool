"""Matplotlib figures used by the interactive Paired T-Test reports."""

from __future__ import annotations

from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as sp_stats

_ACCENT = "#FF8C00"
_DARK = "#303030"
_GRAY = "#A8A8A8"
_GRID = "#D6D6D6"
_GREEN = "#1A8754"
_RED = "#C73A32"


def _style_axis(axis: plt.Axes) -> None:
    axis.set_facecolor("#F7F7F7")
    axis.grid(True, color=_GRID, alpha=0.7, zorder=0)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.tick_params(labelsize=8, colors=_DARK)


def create_paired_summary_figures(
    metrics: dict[str, Any],
) -> tuple[plt.Figure, plt.Figure]:
    """Create the p-value decision gauge and the difference interval plot."""
    p_value = float(metrics["P_Value"])
    alpha = 0.05
    gauge_max = max(0.15, min(1.0, p_value * 1.15))
    fig_gauge, gauge = plt.subplots(figsize=(7.2, 2.4))
    fig_gauge.patch.set_facecolor("#FFFFFF")
    gauge.axhspan(0.25, 0.75, xmin=0, xmax=alpha / gauge_max, color="#F9DDDA", zorder=0)
    gauge.axhspan(0.25, 0.75, xmin=alpha / gauge_max, xmax=1, color="#E8E8E8", zorder=0)
    gauge.axvline(alpha, color=_RED, ls="--", lw=1.5, label="α = 0.05")
    gauge.scatter(min(p_value, gauge_max), 0.5, color=_ACCENT, s=100, zorder=3, label=f"p = {p_value:.4f}")
    gauge.annotate("", xy=(min(p_value, gauge_max), 0.61), xytext=(min(p_value, gauge_max), 0.9), arrowprops={"arrowstyle": "-|>", "color": _DARK})
    gauge.text(alpha / 2, 0.16, "Yes", ha="center", va="center", color=_DARK, fontsize=9, fontweight="bold")
    gauge.text((alpha + gauge_max) / 2, 0.16, "No", ha="center", va="center", color=_DARK, fontsize=9, fontweight="bold")
    gauge.set_xlim(0, gauge_max)
    gauge.set_ylim(0, 1)
    gauge.set_yticks([])
    gauge.set_xlabel("P-value")
    gauge.set_title("Is the difference statistically significant? (α = 0.05)", fontsize=10, fontweight="bold", color=_DARK)
    gauge.legend(loc="upper right", fontsize=8, frameon=False)
    gauge.spines[["top", "right", "left"]].set_visible(False)
    gauge.grid(False)
    fig_gauge.tight_layout()

    mean_difference = float(metrics["Mean_D"])
    ci_lower = float(metrics["CI_Lower"])
    ci_upper = float(metrics["CI_Upper"])
    significant = ci_lower > 0 or ci_upper < 0
    color = _GREEN if significant else _GRAY
    fig_interval, interval = plt.subplots(figsize=(7.2, 2.4))
    fig_interval.patch.set_facecolor("#FFFFFF")
    interval.errorbar(
        [0], [mean_difference],
        yerr=[[mean_difference - ci_lower], [ci_upper - mean_difference]],
        fmt="o", color=color, ecolor=color, capsize=7, markersize=8, lw=2.2, zorder=3,
    )
    interval.axhline(0, color=_DARK, ls="--", lw=1.2, label="No difference")
    interval.set_xlim(-0.8, 0.8)
    interval.set_xticks([0])
    interval.set_xticklabels(["System A − System B"])
    interval.set_ylabel("Difference")
    interval.set_title("95% Confidence Interval for Mean Difference", fontsize=10, fontweight="bold", color=_DARK)
    _style_axis(interval)
    interval.legend(loc="best", fontsize=8, frameon=False)
    fig_interval.tight_layout()
    return fig_gauge, fig_interval


def create_paired_diagnostic_figures(
    paired_df: pd.DataFrame,
    metrics: dict[str, Any],
) -> tuple[plt.Figure, plt.Figure, plt.Figure]:
    """Create paired-value, difference histogram, and chronological run charts."""
    observations = paired_df["Observation"].to_numpy(dtype=float)
    system_a = paired_df["System_A"].to_numpy(dtype=float)
    system_b = paired_df["System_B"].to_numpy(dtype=float)
    differences = paired_df["Difference"].to_numpy(dtype=float)
    mean_difference = float(metrics["Mean_D"])
    std_difference = float(metrics["StDev_D"])

    fig_pairs, pairs = plt.subplots(figsize=(7.2, 4.2))
    fig_pairs.patch.set_facecolor("#FFFFFF")
    for value_a, value_b in zip(system_a, system_b):
        pairs.plot([0, 1], [value_a, value_b], color=_GRAY, alpha=0.6, lw=0.9)
    pairs.scatter(np.zeros(len(system_a)), system_a, color=_DARK, s=24, zorder=3, label="System A")
    pairs.scatter(np.ones(len(system_b)), system_b, color=_ACCENT, s=24, zorder=3, label="System B")
    pairs.set_xlim(-0.25, 1.25)
    pairs.set_xticks([0, 1])
    pairs.set_xticklabels(["System A", "System B"])
    pairs.set_ylabel("Measurement")
    pairs.set_title("Paired Measurements", fontsize=10, fontweight="bold", color=_DARK)
    _style_axis(pairs)
    pairs.legend(loc="best", fontsize=8, frameon=False)
    fig_pairs.tight_layout()

    fig_histogram, histogram = plt.subplots(figsize=(7.2, 4.2))
    fig_histogram.patch.set_facecolor("#FFFFFF")
    counts, bins, patches = histogram.hist(differences, bins=min(12, max(5, int(np.sqrt(len(differences))))), color=_GRAY, edgecolor="#FFFFFF", zorder=2)
    if std_difference > 0:
        centers = (bins[:-1] + bins[1:]) / 2
        for patch, center in zip(patches, centers):
            if abs(center - mean_difference) > 3 * std_difference:
                patch.set_color(_RED)
        x_values = np.linspace(bins[0], bins[-1], 200)
        bin_width = bins[1] - bins[0]
        density = sp_stats.norm.pdf(x_values, mean_difference, std_difference) * len(differences) * bin_width
        histogram.plot(x_values, density, color=_DARK, lw=1.8, label="Normal curve")
    histogram.axvline(0, color=_DARK, ls="--", lw=1.2, label="No difference")
    histogram.axvline(mean_difference, color=_ACCENT, lw=2, label="Mean difference")
    histogram.set_xlabel("System A − System B")
    histogram.set_ylabel("Frequency")
    histogram.set_title("Distribution of Paired Differences", fontsize=10, fontweight="bold", color=_DARK)
    _style_axis(histogram)
    histogram.legend(loc="best", fontsize=8, frameon=False)
    fig_histogram.tight_layout()

    fig_run, run = plt.subplots(figsize=(7.2, 4.2))
    fig_run.patch.set_facecolor("#FFFFFF")
    run.plot(observations, differences, "-o", color=_DARK, markersize=3.5, lw=1.1, zorder=3)
    run.axhline(mean_difference, color=_ACCENT, lw=1.8, label="Mean difference")
    run.axhline(0, color=_DARK, ls="--", lw=1.2, label="No difference")
    run.set_xlabel("Observation order")
    run.set_ylabel("System A − System B")
    run.set_title("Differences by Observation Order", fontsize=10, fontweight="bold", color=_DARK)
    _style_axis(run)
    run.legend(loc="best", fontsize=8, frameon=False)
    fig_run.tight_layout()
    return fig_pairs, fig_histogram, fig_run


def create_paired_worksheet_order_figure(paired_df: pd.DataFrame) -> plt.Figure:
    """Plot both systems in the original worksheet observation order."""
    figure, axis = plt.subplots(figsize=(12, 4.2))
    figure.patch.set_facecolor("#FFFFFF")
    observations = paired_df["Observation"].to_numpy(dtype=float)
    axis.plot(observations, paired_df["System_A"], "o", color=_DARK, ms=4, label="System A")
    axis.plot(observations, paired_df["System_B"], "s", color="#1769AA", ms=4, label="System B")
    axis.set_xlabel("Observation order")
    axis.set_ylabel("Measurement")
    axis.set_title("Paired Data in Worksheet Order", fontsize=10, fontweight="bold", color=_DARK)
    _style_axis(axis)
    axis.legend(loc="upper right", fontsize=8, frameon=False)
    figure.tight_layout()
    return figure


def create_paired_power_figure(diagnostics: dict[str, Any]) -> plt.Figure:
    """Display observed power and detectable differences by target power."""
    figure, (power_axis, detectable_axis) = plt.subplots(1, 2, figsize=(12, 3.8))
    figure.patch.set_facecolor("#FFFFFF")
    observed_power = float(diagnostics["Observed_Power"])
    power_axis.barh(["Observed power"], [observed_power * 100], color=_ACCENT, height=0.45)
    for threshold, color in ((40, _RED), (60, "#F5C84C"), (90, _GREEN)):
        power_axis.axvline(threshold, color=color, lw=1, alpha=0.8)
    power_axis.set_xlim(0, 100)
    power_axis.set_xlabel("Power (%)")
    power_axis.set_title("Chance of Detecting the Observed Difference", fontsize=10, fontweight="bold", color=_DARK)
    _style_axis(power_axis)

    detectable = diagnostics["Detectable_Differences"]
    powers = sorted(detectable)
    detectable_axis.plot(
        [power * 100 for power in powers],
        [float(detectable[power]) for power in powers],
        "-o",
        color=_DARK,
        markerfacecolor=_ACCENT,
        lw=1.5,
    )
    detectable_axis.set_xlabel("Target power (%)")
    detectable_axis.set_ylabel("Detectable mean difference")
    detectable_axis.set_title("Difference Detectable at Each Power", fontsize=10, fontweight="bold", color=_DARK)
    _style_axis(detectable_axis)
    figure.tight_layout()
    return figure
