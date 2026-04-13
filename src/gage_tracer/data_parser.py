"""OGP raw-data parser and TSV exporter.

Reads raw measurement files from OGP SmartScope instruments, extracts
dimension values and tolerance specs, calculates per-dimension stats
(average, range), and writes everything to a tab-separated file for
downstream analysis.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _parse_ogp_data(
    input_file: Path,
) -> tuple[list[dict[str, float]], dict[str, dict[str, float]]]:
    """Read a raw OGP file and split it into repetitions + specs.

    The file uses ``:BEGIN`` / ``:END`` markers to delimit measurement
    repetitions.  Each data line contains the dimension name, measured
    value, nominal, and upper/lower tolerances (tab-separated).

    Lines that start with known metadata prefixes (PATTERN, DISPLAY,
    UNIT, or :markers) are skipped, so any dimension name is accepted.

    Args:
        input_file: Path to the raw OGP text file.

    Returns:
        A tuple ``(repetitions, specs)``:
        - *repetitions*: list of dicts, one per cycle, keyed by dimension.
        - *specs*: dict mapping each dimension to its nominal/tolerance info.
    """
    all_repetitions: list[dict[str, float]] = []
    current_repetition: dict[str, float] = {}
    dimension_specs: dict[str, dict[str, float]] = {}

    with open(input_file, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()

            if line.startswith('":BEGIN"'):
                current_repetition = {}
            elif line.startswith('":END"'):
                if current_repetition:
                    all_repetitions.append(current_repetition)
                    current_repetition = {}
            # Skip known metadata lines; treat everything else as a
            # dimension row (supports any dimension name like gp_height,
            # coplanarity, C5, etc.).
            elif line.startswith('"') and not line.startswith('":') and not line.startswith('"PATTERN') and not line.startswith('"DISPLAY') and not line.startswith('"UNIT'):
                
                parts = line.split("\t")
                if len(parts) >= 5:
                    raw_dim_name = parts[0].strip('"')
                    dim_name = raw_dim_name.replace("_OUT1", "")
                    try:
                        measurement = float(parts[1])
                        nominal = float(parts[2])
                        upper_tol = float(parts[3])
                        lower_tol = float(parts[4])

                        # If this dimension is already in the current
                        # repetition, a new cycle has started (handles
                        # files without :END markers).
                        if dim_name in current_repetition:
                            all_repetitions.append(current_repetition)
                            current_repetition = {}

                        current_repetition[dim_name] = measurement

                        if dim_name not in dimension_specs:
                            dimension_specs[dim_name] = {
                                "nominal": nominal,
                                "upper_tol": upper_tol,
                                "lower_tol": lower_tol,
                            }
                    except ValueError:
                        continue

    # Flush the last repetition if the file didn't end with :END
    if current_repetition:
        all_repetitions.append(current_repetition)

    return all_repetitions, dimension_specs


def _compute_dimension_statistics(
    df: pd.DataFrame,
    specs: dict[str, dict[str, float]],
) -> pd.DataFrame:
    """Calculate average and max range for every dimension.

    Args:
        df: DataFrame with one column per dimension and one row per
            measurement repetition.
        specs: Nominal/tolerance values keyed by dimension name.

    Returns:
        Summary DataFrame with columns: Dimension, Average, Max diff,
        Nominal, Upper Tol, Lower Tol.
    """
    stats: list[dict[str, object]] = []
    for dim in df.columns:
        spec = specs.get(dim, {"nominal": "", "upper_tol": "", "lower_tol": ""})
        stats.append(
            {
                "Dimension": dim,
                "Average": df[dim].mean(),
                "Max diff": df[dim].max() - df[dim].min(),
                "Nominal": spec["nominal"],
                "Upper Tol": spec["upper_tol"],
                "Lower Tol": spec["lower_tol"],
            }
        )
    return pd.DataFrame(stats)


def _build_interleaved_output(
    df: pd.DataFrame,
    stats_df: pd.DataFrame,
) -> pd.DataFrame:
    """Merge raw data and stats side-by-side for the output TSV.

    The final layout looks like:
    ``[measurement columns] | [2 blank spacer cols] | [stats columns]``

    Args:
        df: Measurement data (one column per dimension).
        stats_df: Pre-computed per-dimension statistics.

    Returns:
        A combined DataFrame ready to be exported as TSV.
    """
    combined_df = df.copy()

    combined_df[""] = ""
    combined_df[" "] = ""

    for col in ("Dimension", "Average", "Max diff", "Nominal", "Upper Tol", "Lower Tol"):
        combined_df[col] = pd.Series(dtype="object", index=combined_df.index)

    for idx, row in stats_df.iterrows():
        combined_df.loc[idx, "Dimension"] = row["Dimension"]
        combined_df.loc[idx, "Average"] = row["Average"]
        combined_df.loc[idx, "Max diff"] = row["Max diff"]
        combined_df.loc[idx, "Nominal"] = row["Nominal"]
        combined_df.loc[idx, "Upper Tol"] = row["Upper Tol"]
        combined_df.loc[idx, "Lower Tol"] = row["Lower Tol"]

    return combined_df


def _format_output_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Round numeric values to a consistent number of decimal places.

    Measurement columns get 7 decimals; stats columns get 8 decimals.
    Blank or NaN cells are left empty.

    Args:
        df: Mixed DataFrame (measurements + stats).

    Returns:
        The same DataFrame with all numbers formatted as strings.
    """
    for col in df.columns:
        if col in ("", " ", "Dimension"):
            continue
        elif col in ("Average", "Max diff", "Nominal", "Upper Tol", "Lower Tol"):

            def _fmt_stats(x: float | str) -> str:
                if pd.isna(x) or (isinstance(x, str) and x == ""):
                    return ""
                return f"{float(x):.8f}"

            df[col] = df[col].apply(_fmt_stats)
        else:

            def _fmt_meas(x: float | str) -> str:
                if pd.isna(x) or (isinstance(x, str) and x == ""):
                    return ""
                return f"{float(x):.7f}"

            df[col] = df[col].apply(_fmt_meas)

    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def transform_ogp_data(input_file: Path, output_file: Path) -> None:
    """Convert a raw OGP file into a structured TSV.

    This is the main function of the module.  It reads the raw OGP
    measurements, runs basic statistics, and writes an interleaved
    data + stats table that the rest of the pipeline consumes.

    Args:
        input_file: Path to the raw OGP data file.
        output_file: Where to write the resulting TSV.
    """
    all_repetitions, specs = _parse_ogp_data(input_file)
    df = pd.DataFrame(all_repetitions)
    stats_df = _compute_dimension_statistics(df, specs)
    combined_df = _build_interleaved_output(df, stats_df)
    combined_df = _format_output_dataframe(combined_df)

    combined_df.to_csv(output_file, sep="\t", index=False)

    print(f"Success! Processed {len(all_repetitions)} repetitions.")
    print(f"Detected {len(df.columns)} unique dimensions: {', '.join(df.columns)}")
    print(f"Data saved to '{output_file}'")
