"""Pure statistical functions for the Type 1 Gage Study.

Every function here is a pure calculation — numbers in, numbers out.
No file I/O, no plotting, no side effects.

IMPORTANT: These formulas (Cg, Cgk, %Var, etc.) must match Minitab’s
Type 1 Gage Study output exactly.  Don’t tweak the math without first
verifying against a Minitab reference run.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def compute_bias_significance(
    bias: float,
    std_dev: float,
    sample_size: int,
) -> tuple[float, float]:
    """Test whether the measured bias is statistically significant.

    Performs a two-sided t-test for H₀: bias = 0 using a Student-t
    distribution with (n − 1) degrees of freedom.  If SciPy isn’t
    installed, falls back to a normal approximation.

    Args:
        bias: Mean − Reference.
        std_dev: Sample standard deviation (ddof=1).
        sample_size: Number of measurements.

    Returns:
        ``(t_value, p_value)`` tuple.
    """
    if sample_size <= 1 or pd.isna(std_dev) or std_dev <= 0:
        if abs(bias) < 1e-12:
            return 0.0, 1.0
        return float("inf"), 0.0

    t_value: float = bias / (std_dev / math.sqrt(sample_size))

    try:
        from scipy import stats as sp_stats

        p_value = float(2 * sp_stats.t.sf(abs(t_value), df=sample_size - 1))
    except Exception:
        p_value = float(math.erfc(abs(t_value) / math.sqrt(2)))

    return float(t_value), float(p_value)


def calculate_type1_metrics(
    dim: str,
    measurements: pd.Series,
    spec_row: pd.Series,
) -> dict[str, object]:
    """Compute all Minitab-style Type 1 Gage Study metrics for one dimension.

    Given a dimension’s measurements and its tolerance spec, this function
    returns a full result dictionary with Cg, Cgk, bias significance,
    %Var, and an ACCEPT/REJECT status.

    Args:
        dim: Dimension name (e.g. ``"gp_height"``, ``"C5"``).
        measurements: Clean numeric series for this dimension.
        spec_row: Row from the intermediate TSV with ``Nominal``,
            ``Upper Tol``, ``Lower Tol`` (and optionally ``Reference``
            or ``Average``).

    Returns:
        Dict with all computed metrics.  Key fields:
        Cg, Cgk, Bias, T, PValue, %Var(Repeatability), Status, etc.
    """
    nominal: float = float(spec_row["Nominal"])
    upper_tol: float = float(spec_row["Upper Tol"])
    lower_tol: float = float(spec_row["Lower Tol"])

    sample_size: int = int(len(measurements))
    mean: float = float(measurements.mean())
    std_dev: float = float(measurements.std()) if sample_size > 1 else 0.0
    if pd.isna(std_dev):
        std_dev = 0.0

    max_diff: float = (
        float(measurements.max() - measurements.min()) if sample_size > 0 else 0.0
    )

    # Tolerance = the larger absolute tolerance bound (Minitab convention).
    tolerance: float = max(abs(upper_tol), abs(lower_tol))
    study_var: float = 6 * std_dev  # 6σ study variation

    # Reference resolution: prefer an explicit Reference value, then the
    # average from the stats row, and fall back to the sample mean.
    if "Reference" in spec_row and pd.notna(spec_row["Reference"]):
        reference: float = float(spec_row["Reference"])
    elif "Average" in spec_row and pd.notna(spec_row["Average"]):
        reference = float(spec_row["Average"])
    else:
        reference = mean

    bias: float = mean - reference
    t_value, p_value = compute_bias_significance(bias, std_dev, sample_size)

    cg: float = (
        (0.2 * tolerance) / study_var if study_var > 0 and tolerance > 0 else 0.0
    )
    cgk: float = (
        (0.1 * tolerance - abs(bias)) / (3 * std_dev)
        if std_dev > 0 and tolerance > 0
        else 0.0
    )

    repeatability_pct: float | None = (
        (study_var / tolerance * 100) if tolerance > 0 else None
    )
    repeatability_bias_pct: float | None = (
        6 * math.sqrt(std_dev**2 + bias**2) / tolerance * 100
        if tolerance > 0
        else None
    )

    return {
        "Gage Item": dim,
        "Reference": reference,
        "Mean": mean,
        "Bias": bias,
        "T": t_value,
        "PValue": p_value,
        "StdDev": std_dev,
        "6 x StdDev (SV)": study_var,
        "Tolerance (Tol)": tolerance,
        "Max diff": max_diff,
        "Cg": cg,
        "Cgk": cgk,
        "%Var(Repeatability)": repeatability_pct,
        "%Var(Repeatability and Bias)": repeatability_bias_pct,
        "Observations": sample_size,
        "Nominal": nominal,
        "Upper Tol": upper_tol,
        "Lower Tol": lower_tol,
        "Ref + 0.10*Tol": reference + 0.1 * tolerance,
        "Ref - 0.10*Tol": reference - 0.1 * tolerance,
        "Status": "ACCEPT" if cg >= 1.33 and cgk >= 1.33 else "REJECT",
    }
