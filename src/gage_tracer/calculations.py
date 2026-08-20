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


# ---------------------------------------------------------------------------
# Gage R&R Crossed ANOVA (Minitab Standard)
# ---------------------------------------------------------------------------

def calculate_gage_rr_crossed(
    df: pd.DataFrame,
    tolerance: float,
    alpha_pool: float = 0.05,
    sigma_multiplier: float = 6.0,
) -> dict[str, object]:
    """Compute Gage R&R Crossed ANOVA analysis following Minitab standards.

    Performs Two-Way ANOVA with Part and Operator factors, applies Minitab's
    pooling rule for Part*Operator interaction, and calculates variance components
    and evaluation metrics.

    Args:
        df: DataFrame with columns: Part, Operator, Measurement.
        tolerance: Total tolerance range (USL - LSL).
        alpha_pool: Significance level for interaction pooling (default 0.05).
        sigma_multiplier: Multiplier for study variation (default 6.0).

    Returns:
        Dictionary containing:
        - 'anova_table': DataFrame with ANOVA results (SS, DF, MS, F, P)
        - 'variance_components': DataFrame with variance components
        - 'gage_evaluation': DataFrame with %Contribution, %Study Var, %Tolerance
        - 'ndc': Number of Distinct Categories
        - 'pooled_interaction': Boolean indicating if interaction was pooled
        - 'interaction_p_value': P-value of Part*Operator interaction
        - 'total_grr_pct': Total Gage R&R as percentage of study variation
        - 'study_variation': Total study variation (6*SD)
    """
    try:
        from scipy import stats as sp_stats
    except Exception:
        raise ImportError("scipy is required for Gage R&R ANOVA calculations")

    # Extract data
    parts = df["Part"].values
    operators = df["Operator"].values
    measurements = df["Measurement"].values

    # Get unique levels
    unique_parts = sorted(df["Part"].unique())
    unique_operators = sorted(df["Operator"].unique())

    n_parts = len(unique_parts)
    n_operators = len(unique_operators)
    n_trials = len(df) // (n_parts * n_operators)  # Should be 3

    # Grand mean
    grand_mean = np.mean(measurements)

    # Calculate sums of squares
    # SS_Total
    ss_total = np.sum((measurements - grand_mean) ** 2)

    # SS_Part (between parts)
    part_means = df.groupby("Part")["Measurement"].mean()
    ss_part = n_operators * n_trials * np.sum((part_means - grand_mean) ** 2)

    # SS_Operator (between operators)
    operator_means = df.groupby("Operator")["Measurement"].mean()
    ss_operator = n_parts * n_trials * np.sum((operator_means - grand_mean) ** 2)

    # SS_Part*Operator (interaction)
    # Calculate cell means for each Part-Operator combination
    cell_means = df.groupby(["Part", "Operator"])["Measurement"].mean().reset_index()
    cell_means = cell_means.pivot(index="Part", columns="Operator", values="Measurement")

    # Expected values under no interaction
    expected = np.outer(part_means - grand_mean, np.ones(n_operators)) + \
               np.outer(np.ones(n_parts), operator_means - grand_mean) + grand_mean

    ss_interaction = n_trials * np.sum((cell_means.values - expected) ** 2)

    # SS_Error (repeatability)
    ss_error = ss_total - ss_part - ss_operator - ss_interaction

    # Degrees of freedom
    df_total = len(measurements) - 1
    df_part = n_parts - 1
    df_operator = n_operators - 1
    df_interaction = df_part * df_operator
    df_error = df_total - df_part - df_operator - df_interaction

    # Mean squares
    ms_part = ss_part / df_part if df_part > 0 else 0
    ms_operator = ss_operator / df_operator if df_operator > 0 else 0
    ms_interaction = ss_interaction / df_interaction if df_interaction > 0 else 0
    ms_error = ss_error / df_error if df_error > 0 else 0

    # F-statistics and p-values
    f_part = ms_part / ms_error if ms_error > 0 else 0
    f_operator = ms_operator / ms_error if ms_error > 0 else 0
    f_interaction = ms_interaction / ms_error if ms_error > 0 else 0

    p_part = float(sp_stats.f.sf(f_part, df_part, df_error)) if ms_error > 0 else 1.0
    p_operator = float(sp_stats.f.sf(f_operator, df_operator, df_error)) if ms_error > 0 else 1.0
    p_interaction = float(sp_stats.f.sf(f_interaction, df_interaction, df_error)) if ms_error > 0 else 1.0

    # Minitab pooling rule: pool interaction if p-value > alpha_pool
    pooled_interaction = p_interaction > alpha_pool

    if pooled_interaction:
        # Pool interaction with error
        ss_error_pooled = ss_error + ss_interaction
        df_error_pooled = df_error + df_interaction
        ms_error_pooled = ss_error_pooled / df_error_pooled if df_error_pooled > 0 else 0

        # Recalculate F-statistics with pooled error
        f_part = ms_part / ms_error_pooled if ms_error_pooled > 0 else 0
        f_operator = ms_operator / ms_error_pooled if ms_error_pooled > 0 else 0

        p_part = float(sp_stats.f.sf(f_part, df_part, df_error_pooled)) if ms_error_pooled > 0 else 1.0
        p_operator = float(sp_stats.f.sf(f_operator, df_operator, df_error_pooled)) if ms_error_pooled > 0 else 1.0

        ms_error_final = ms_error_pooled
        df_error_final = df_error_pooled
    else:
        ms_error_final = ms_error
        df_error_final = df_error

    # Variance components (Minitab method)
    # Repeatability (Equipment Variation, EV)
    var_repeatability = ms_error_final

    # Reproducibility (Appraiser Variation, AV)
    if n_operators > 1:
        var_reproducibility = (ms_operator - var_repeatability) / (n_parts * n_trials)
        if var_reproducibility < 0:
            var_reproducibility = 0
    else:
        var_reproducibility = 0

    # Part-to-Part (PV)
    if n_parts > 1:
        var_part = (ms_part - ms_error_final) / (n_operators * n_trials)
        if var_part < 0:
            var_part = 0
    else:
        var_part = 0

    # Total Gage R&R
    var_grr = var_repeatability + var_reproducibility

    # Total Variation
    var_total = var_grr + var_part

    # Standard deviations
    sd_repeatability = np.sqrt(var_repeatability)
    sd_reproducibility = np.sqrt(var_reproducibility)
    sd_grr = np.sqrt(var_grr)
    sd_part = np.sqrt(var_part)
    sd_total = np.sqrt(var_total)

    # Study variations (6*SD)
    sv_repeatability = sigma_multiplier * sd_repeatability
    sv_reproducibility = sigma_multiplier * sd_reproducibility
    sv_grr = sigma_multiplier * sd_grr
    sv_part = sigma_multiplier * sd_part
    sv_total = sigma_multiplier * sd_total

    # Percentage calculations
    # % Contribution (variance based)
    pct_contrib_repeatability = (var_repeatability / var_total * 100) if var_total > 0 else 0
    pct_contrib_reproducibility = (var_reproducibility / var_total * 100) if var_total > 0 else 0
    pct_contrib_grr = (var_grr / var_total * 100) if var_total > 0 else 0
    pct_contrib_part = (var_part / var_total * 100) if var_total > 0 else 0

    # % Study Variation (6*SD based)
    pct_study_repeatability = (sv_repeatability / sv_total * 100) if sv_total > 0 else 0
    pct_study_reproducibility = (sv_reproducibility / sv_total * 100) if sv_total > 0 else 0
    pct_study_grr = (sv_grr / sv_total * 100) if sv_total > 0 else 0
    pct_study_part = (sv_part / sv_total * 100) if sv_total > 0 else 0

    # % Tolerance (tolerance based)
    pct_tol_repeatability = (sv_repeatability / tolerance * 100) if tolerance > 0 else 0
    pct_tol_reproducibility = (sv_reproducibility / tolerance * 100) if tolerance > 0 else 0
    pct_tol_grr = (sv_grr / tolerance * 100) if tolerance > 0 else 0
    pct_tol_part = (sv_part / tolerance * 100) if tolerance > 0 else 0

    # Number of Distinct Categories (NDC)
    if sd_grr > 0:
        ndc = 1.41 * (sd_part / sd_grr)
        ndc = math.floor(ndc) if ndc >= 1 else 1
    else:
        ndc = 0

    # Build ANOVA table DataFrame
    anova_data = [
        {
            "Source": "Part",
            "DF": df_part,
            "SS": ss_part,
            "MS": ms_part,
            "F": f_part,
            "P": p_part,
        },
        {
            "Source": "Operator",
            "DF": df_operator,
            "SS": ss_operator,
            "MS": ms_operator,
            "F": f_operator,
            "P": p_operator,
        },
        {
            "Source": "Part * Operator",
            "DF": df_interaction,
            "SS": ss_interaction,
            "MS": ms_interaction,
            "F": f_interaction,
            "P": p_interaction,
        },
        {
            "Source": "Error",
            "DF": df_error_final,
            "SS": ss_error if not pooled_interaction else ss_error + ss_interaction,
            "MS": ms_error_final,
            "F": "",
            "P": "",
        },
        {
            "Source": "Total",
            "DF": df_total,
            "SS": ss_total,
            "MS": "",
            "F": "",
            "P": "",
        },
    ]
    anova_df = pd.DataFrame(anova_data)

    # Build variance components DataFrame
    variance_data = [
        {
            "Source": "Total Gage R&R",
            "VarComp": var_grr,
            "StdDev": sd_grr,
            "StudyVar": sv_grr,
            "%StudyVar": pct_study_grr,
            "%Contribution": pct_contrib_grr,
            "%Tolerance": pct_tol_grr,
        },
        {
            "Source": "Repeatability",
            "VarComp": var_repeatability,
            "StdDev": sd_repeatability,
            "StudyVar": sv_repeatability,
            "%StudyVar": pct_study_repeatability,
            "%Contribution": pct_contrib_repeatability,
            "%Tolerance": pct_tol_repeatability,
        },
        {
            "Source": "Reproducibility",
            "VarComp": var_reproducibility,
            "StdDev": sd_reproducibility,
            "StudyVar": sv_reproducibility,
            "%StudyVar": pct_study_reproducibility,
            "%Contribution": pct_contrib_reproducibility,
            "%Tolerance": pct_tol_reproducibility,
        },
        {
            "Source": "Part-to-Part",
            "VarComp": var_part,
            "StdDev": sd_part,
            "StudyVar": sv_part,
            "%StudyVar": pct_study_part,
            "%Contribution": pct_contrib_part,
            "%Tolerance": pct_tol_part,
        },
        {
            "Source": "Total Variation",
            "VarComp": var_total,
            "StdDev": sd_total,
            "StudyVar": sv_total,
            "%StudyVar": 100.0,
            "%Contribution": 100.0,
            "%Tolerance": (sv_total / tolerance * 100) if tolerance > 0 else 0,
        },
    ]
    variance_df = pd.DataFrame(variance_data)

    # Build gage evaluation DataFrame (Minitab format)
    gage_eval_data = [
        {
            "Source": "Total Gage R&R",
            "%Contribution": f"{pct_contrib_grr:.4f}%",
            "%Study Var": f"{pct_study_grr:.4f}%",
            "%Tolerance": f"{pct_tol_grr:.4f}%",
        },
        {
            "Source": "Repeatability",
            "%Contribution": f"{pct_contrib_repeatability:.4f}%",
            "%Study Var": f"{pct_study_repeatability:.4f}%",
            "%Tolerance": f"{pct_tol_repeatability:.4f}%",
        },
        {
            "Source": "Reproducibility",
            "%Contribution": f"{pct_contrib_reproducibility:.4f}%",
            "%Study Var": f"{pct_study_reproducibility:.4f}%",
            "%Tolerance": f"{pct_tol_reproducibility:.4f}%",
        },
        {
            "Source": "Part-to-Part",
            "%Contribution": f"{pct_contrib_part:.4f}%",
            "%Study Var": f"{pct_study_part:.4f}%",
            "%Tolerance": f"{pct_tol_part:.4f}%",
        },
    ]
    gage_eval_df = pd.DataFrame(gage_eval_data)

    return {
        "anova_table": anova_df,
        "variance_components": variance_df,
        "gage_evaluation": gage_eval_df,
        "ndc": ndc,
        "pooled_interaction": pooled_interaction,
        "interaction_p_value": p_interaction,
        "total_grr_pct": pct_study_grr,
        "study_variation": sv_total,
        "tolerance": tolerance,
        "n_parts": n_parts,
        "n_operators": n_operators,
        "n_trials": n_trials,
    }
