"""Raw data parser and TSV exporter.

Reads raw measurement files, extracts
dimension values and tolerance specs, calculates per-dimension stats
(average, range), and writes everything to a tab-separated file for
downstream analysis.
"""

from __future__ import annotations

from io import StringIO, TextIOBase
from pathlib import Path
from typing import IO, TextIO, Union

import pandas as pd

_InputSource = Union[Path, str, TextIO, IO[bytes]]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _open_text_input(input_file: _InputSource) -> TextIO:
    """Open a text input source from a path or in-memory text/binary stream."""
    if isinstance(input_file, (Path, str)):
        return open(input_file, "r", encoding="utf-8")

    if hasattr(input_file, "read"):
        if isinstance(input_file, (StringIO, TextIOBase)):
            try:
                input_file.seek(0)
            except Exception:
                pass
            return input_file

        raw = input_file.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        return StringIO(raw)

    raise TypeError("input_file must be a path or a text/binary stream")


def _parse_raw_data(
    input_file: _InputSource,
) -> tuple[list[dict[str, float]], dict[str, dict[str, float]]]:
    """Read a raw data file and split it into repetitions + specs.

    The file uses ``:BEGIN`` / ``:END`` markers to delimit measurement
    repetitions.  Each data line contains the dimension name, measured
    value, nominal, and upper/lower tolerances (tab-separated).

    Supports files without markers by detecting cycle boundaries when a
    dimension repeats (indicating a new cycle).

    Lines that start with known metadata prefixes (PATTERN, DISPLAY,
    UNIT, or :markers) are skipped, so any dimension name is accepted.

    Args:
        input_file: Path to the raw data text file.

    Returns:
        A tuple ``(repetitions, specs)``:
        - *repetitions*: list of dicts, one per cycle, keyed by dimension.
        - *specs*: dict mapping each dimension to its nominal/tolerance info.
    """
    all_repetitions: list[dict[str, float]] = []
    current_repetition: dict[str, float] = {}
    dimension_specs: dict[str, dict[str, float]] = {}
    first_dimension_in_cycle: str | None = None
    has_explicit_markers = False

    with _open_text_input(input_file) as fh:
        for line in fh:
            line = line.strip()

            if line.startswith('":BEGIN"'):
                has_explicit_markers = True
                current_repetition = {}
                first_dimension_in_cycle = None
            elif line.startswith('":END"'):
                has_explicit_markers = True
                if current_repetition:
                    all_repetitions.append(current_repetition)
                    current_repetition = {}
                    first_dimension_in_cycle = None
            # Skip known metadata lines; treat everything else as a
            # dimension row (supports any dimension name like gp_height,
            # coplanarity, C5, etc.).
            elif line.startswith('"'):
                # Check if it's a metadata line by looking at the content inside quotes
                stripped_line = line[1:].split('"')[0].strip() if line.startswith('"') else line
                if stripped_line.startswith(':') or stripped_line in ('PATTERN', 'DISPLAY', 'UNIT') or stripped_line.startswith(('PATTERN:', 'DISPLAY:', 'UNIT:')):
                    continue
                
                parts = line.split("\t")
                # Handle both formats: with specs (5+ parts) and without (2 parts)
                if len(parts) >= 2:
                    raw_dim_name = parts[0].strip('"')
                    dim_name = raw_dim_name.replace("_OUT1", "")
                    try:
                        # Skip if measurement is empty
                        if not parts[1].strip():
                            continue
                        measurement = float(parts[1])

                        # Detect cycle boundary: if this dimension already
                        # exists in current repetition, start a new cycle
                        # (works for files without explicit markers)
                        if dim_name in current_repetition:
                            if current_repetition:
                                all_repetitions.append(current_repetition)
                            current_repetition = {}
                            first_dimension_in_cycle = dim_name

                        # Track the first dimension we see in each cycle
                        if first_dimension_in_cycle is None:
                            first_dimension_in_cycle = dim_name

                        current_repetition[dim_name] = measurement

                        # Only update specs if we have full spec data (5+ parts)
                        if len(parts) >= 5:
                            try:
                                nominal = float(parts[2])
                                upper_tol = float(parts[3])
                                lower_tol = float(parts[4])

                                if dim_name not in dimension_specs:
                                    dimension_specs[dim_name] = {
                                        "nominal": nominal,
                                        "upper_tol": upper_tol,
                                        "lower_tol": lower_tol,
                                    }
                            except (ValueError, IndexError):
                                pass
                        # For files without specs, initialize default specs
                        elif dim_name not in dimension_specs:
                            dimension_specs[dim_name] = {
                                "nominal": "",
                                "upper_tol": "",
                                "lower_tol": "",
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

def transform_raw_data(
    input_file: _InputSource,
    output_file: Path | None = None,
) -> pd.DataFrame:
    """Convert a raw data source into a structured TSV or return a DataFrame.

    This is the main function of the module. It reads the raw
    measurements, runs basic statistics, and writes an interleaved
    data + stats table to disk if ``output_file`` is provided.

    Args:
        input_file: Path, filename, or in-memory text/binary stream.
        output_file: Where to write the resulting TSV, or ``None`` to skip.

    Returns:
        The parsed and formatted DataFrame.
    """
    all_repetitions, specs = _parse_raw_data(input_file)
    df = pd.DataFrame(all_repetitions)
    stats_df = _compute_dimension_statistics(df, specs)
    combined_df = _build_interleaved_output(df, stats_df)
    combined_df = _format_output_dataframe(combined_df)

    if output_file is not None:
        combined_df.to_csv(output_file, sep="\t", index=False)
        print(f"Success! Processed {len(all_repetitions)} repetitions.")
        print(f"Detected {len(df.columns)} unique dimensions: {', '.join(df.columns)}")
        print(f"Data saved to '{output_file}'")

    return combined_df
