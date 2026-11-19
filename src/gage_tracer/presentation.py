"""Pure presentation adapters for reports and browser interfaces.

These helpers format domain results for display without importing UI frameworks.
That keeps the UI layer thin and makes formatting behavior directly testable.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

import pandas as pd

from .calculations import calculate_type1_metrics


def metric_status(value: float, threshold: float) -> str:
    """Return the display status for a thresholded metric."""
    return "PASS" if value >= threshold else "FAIL"


def format_numeric_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Format numeric columns consistently without changing the source values."""
    formatted = frame.copy()
    for column in columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        nonzero = [abs(float(value)) for value in values if pd.notna(value) and math.isfinite(float(value)) and value != 0]
        decimals = max(5, 1 - Decimal(str(min(nonzero))).adjusted()) if nonzero else 5
        scientific = decimals > 8

        def display(value: float) -> str:
            if pd.isna(value):
                return ""
            if not math.isfinite(value):
                return str(value)
            result = f"{value:.5e}" if scientific else f"{value:.{decimals}f}"
            if result.startswith("-") and float(result) == 0:
                return result[1:]
            return result

        formatted[column] = values.map(display)
    return formatted


def format_float_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Format floating-point columns while retaining integer identifiers and counts."""
    return format_numeric_columns(frame, list(frame.select_dtypes(include="floating").columns))


def format_numeric_value(value: float) -> str:
    """Format an individual displayed value using the shared precision rule."""
    return format_numeric_columns(pd.DataFrame({"value": [value]}), ["value"]).iloc[0, 0]


def format_gage_evaluation(results: dict[str, Any]) -> pd.DataFrame:
    """Present evaluation percentages from the full-precision variance components."""
    frame = results["variance_components"].iloc[:5][
        ["Source", "%Contribution", "%StudyVar", "%Tolerance"]
    ].rename(columns={"%StudyVar": "%Study Var"})
    columns = ["%Contribution", "%Study Var", "%Tolerance"]
    formatted = format_numeric_columns(frame, columns)
    for column in columns:
        formatted[column] = formatted[column] + "%"
    return formatted


def format_type1_dataframe(summary_df: pd.DataFrame) -> pd.DataFrame:
    """Format Type 1 results for the summary table."""
    display_df = summary_df[
        ["Gage Item", "Reference", "Mean", "StdDev", "Bias", "T", "PValue", "Cg", "Cgk"]
    ].copy()
    display_df = format_numeric_columns(display_df, [column for column in display_df if column != "Gage Item"])
    return display_df.set_index("Gage Item")


def paired_descriptive_dataframe(metrics: dict[str, Any]) -> pd.DataFrame:
    """Format the three-row descriptive statistics table for Paired T reports."""
    frame = pd.DataFrame(
        [
            {"Variable": "System A", "N": int(metrics["N"]), "Mean": metrics['Mean_A'], "StDev": metrics['StDev_A'], "SE Mean": metrics['SE_A']},
            {"Variable": "System B", "N": int(metrics["N"]), "Mean": metrics['Mean_B'], "StDev": metrics['StDev_B'], "SE Mean": metrics['SE_B']},
            {"Variable": "Difference (A − B)", "N": int(metrics["N"]), "Mean": metrics['Mean_D'], "StDev": metrics['StDev_D'], "SE Mean": metrics['SE_D']},
        ]
    )
    return format_numeric_columns(frame, ["Mean", "StDev", "SE Mean"])


def paired_outliers_dataframe(
    paired_df: pd.DataFrame,
    outlier_positions: list[int],
) -> pd.DataFrame:
    """Return the severe paired-difference outliers for display."""
    if not outlier_positions:
        return pd.DataFrame(columns=["Observation", "System A", "System B", "Difference (A − B)"])
    outliers = paired_df[paired_df["Observation"].isin(outlier_positions)].copy()
    return outliers.rename(
        columns={
            "System_A": "System A",
            "System_B": "System B",
            "Difference": "Difference (A − B)",
        }
    )


def format_paired_preview(paired_df: pd.DataFrame, max_rows: int = 10) -> pd.DataFrame:
    """Format the paired measurements for a readable web preview."""
    preview = format_numeric_columns(paired_df, ["System_A", "System_B", "Difference"]).head(max_rows)
    return preview.rename(
        columns={
            "Observation": "Obs",
            "System_A": "System A",
            "System_B": "System B",
            "Difference": "A − B",
        }
    )


def paired_data_quality_summary(paired_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize the uploaded paired data ranges and variation."""
    differences = pd.to_numeric(paired_df["Difference"], errors="coerce").dropna()
    system_a = pd.to_numeric(paired_df["System_A"], errors="coerce").dropna()
    system_b = pd.to_numeric(paired_df["System_B"], errors="coerce").dropna()
    return pd.DataFrame(
        [
            {"Check": "Paired observations", "Value": str(len(paired_df))},
            {"Check": "System A range", "Value": f"{system_a.min():.6f} to {system_a.max():.6f}"},
            {"Check": "System B range", "Value": f"{system_b.min():.6f} to {system_b.max():.6f}"},
            {"Check": "Difference range", "Value": f"{differences.min():+.6f} to {differences.max():+.6f}"},
            {"Check": "Zero differences", "Value": str(int((differences.abs() < 1e-12).sum()))},
        ]
    ).set_index("Check")


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
