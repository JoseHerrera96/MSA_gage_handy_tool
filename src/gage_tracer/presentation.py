"""Pure presentation adapters for the Streamlit application.

These helpers format domain results for display without importing Streamlit.
That keeps the UI layer thin and makes formatting behavior directly testable.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .calculations import calculate_type1_metrics


def metric_status(value: float, threshold: float) -> str:
    """Return the display status for a thresholded metric."""
    return "PASS" if value >= threshold else "FAIL"


def format_type1_dataframe(summary_df: pd.DataFrame) -> pd.DataFrame:
    """Format Type 1 results for the summary table."""
    display_df = summary_df[
        ["Gage Item", "Reference", "Mean", "StdDev", "Bias", "T", "PValue", "Cg", "Cgk"]
    ].copy()
    display_df["PValue"] = display_df["PValue"].map("{:.6f}".format)
    display_df["Bias"] = display_df["Bias"].map("{:+.6f}".format)
    return display_df.set_index("Gage Item")


def paired_summary_dataframe(metrics: dict[str, Any]) -> pd.DataFrame:
    """Format paired t-test metrics for the summary table."""
    return (
        pd.DataFrame(
            [
                {"Metric": "N", "System A": int(metrics["N"]), "System B": int(metrics["N"]), "Difference": ""},
                {"Metric": "Mean", "System A": f"{metrics['Mean_A']:.6f}", "System B": f"{metrics['Mean_B']:.6f}", "Difference": f"{metrics['Mean_D']:.6f}"},
                {"Metric": "StDev", "System A": f"{metrics['StDev_A']:.6f}", "System B": f"{metrics['StDev_B']:.6f}", "Difference": f"{metrics['StDev_D']:.6f}"},
                {"Metric": "SE Mean", "System A": f"{metrics['SE_A']:.6f}", "System B": f"{metrics['SE_B']:.6f}", "Difference": f"{metrics['SE_D']:.6f}"},
                {"Metric": "95% CI Lower", "System A": "", "System B": "", "Difference": f"{metrics['CI_Lower']:.6f}"},
                {"Metric": "95% CI Upper", "System A": "", "System B": "", "Difference": f"{metrics['CI_Upper']:.6f}"},
                {"Metric": "T-Value", "System A": "", "System B": "", "Difference": f"{metrics['T_Value']:.6f}"},
                {"Metric": "Degrees of Freedom", "System A": "", "System B": "", "Difference": int(metrics["DF"])},
                {"Metric": "P-Value", "System A": "", "System B": "", "Difference": f"{metrics['P_Value']:.6f}"},
            ]
        )
        .set_index("Metric")
    )


def build_type1_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Calculate Type 1 metrics from the normalized parser output."""
    skip_cols = {"", " ", "Dimension", "Average", "Max diff", "Nominal", "Upper Tol", "Lower Tol"}
    summary: list[dict[str, Any]] = []
    for col in df.columns:
        if col.strip() in skip_cols:
            continue
        measurements = pd.to_numeric(df[col], errors="coerce").dropna()
        if measurements.empty:
            continue

        spec_row = df[df["Dimension"] == col].iloc[0].copy()
        for field in ("Nominal", "Upper Tol", "Lower Tol"):
            spec_row[field] = pd.to_numeric(spec_row[field], errors="coerce")
        if any(pd.isna(spec_row[field]) for field in ("Nominal", "Upper Tol", "Lower Tol")):
            raise ValueError(
                f"Missing or invalid tolerance specs for dimension '{col}'. "
                "Please upload a raw data file with nominal and tolerance values."
            )
        summary.append(calculate_type1_metrics(col, measurements, spec_row))
    return summary
