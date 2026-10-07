"""Raw data parser and TSV exporter.

Reads raw measurement files, extracts
dimension values and tolerance specs, calculates per-dimension stats
(average, range), and writes everything to a tab-separated file for
downstream analysis.
"""

from __future__ import annotations

import re
import math
from io import StringIO, TextIOBase
from pathlib import Path
from typing import IO, TextIO, Union

import pandas as pd

from .study_config import GRR_DESIGN

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
            elif line.startswith('"'):
                stripped_line = line[1:].split('"')[0].strip()
                if stripped_line.startswith(':') or stripped_line in ('PATTERN', 'DISPLAY', 'UNIT') or stripped_line.startswith(('PATTERN:', 'DISPLAY:', 'UNIT:')):
                    continue

                parts = line.split("\t")
                if len(parts) >= 2:
                    raw_dim_name = parts[0].strip('"')
                    dim_name = raw_dim_name.replace("_OUT1", "")
                    try:
                        if not parts[1].strip():
                            continue
                        measurement = float(parts[1])

                        if dim_name in current_repetition:
                            if current_repetition:
                                all_repetitions.append(current_repetition)
                            current_repetition = {}
                            first_dimension_in_cycle = dim_name

                        if first_dimension_in_cycle is None:
                            first_dimension_in_cycle = dim_name

                        current_repetition[dim_name] = measurement

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
                        elif dim_name not in dimension_specs:
                            dimension_specs[dim_name] = {
                                "nominal": "",
                                "upper_tol": "",
                                "lower_tol": "",
                            }
                    except ValueError:
                        continue

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


# ---------------------------------------------------------------------------
# Gage R&R Crossed Parser
# ---------------------------------------------------------------------------

def _parse_gage_rr_row(line: str) -> dict[str, object] | None:
    """Parse one GRR measurement row, ignoring headers and footers."""
    parts = line.split("\t")
    if len(parts) < 5:
        return None
    try:
        characteristic = parts[0].strip().strip('"')
        if not characteristic:
            return None
        return {
            "Characteristic": characteristic,
            "Measurement": float(parts[1]),
            "Nominal": float(parts[2]),
            "Upper Tol": float(parts[3]),
            "Lower Tol": float(parts[4]),
        }
    except (ValueError, IndexError):
        return None


def _is_gage_rr_marker(line: str, marker: str) -> bool:
    normalized = line.strip().strip('"')
    return normalized.startswith(marker) or normalized.startswith(marker.lstrip(":"))


def _validate_gage_rr_block(
    block_records: list[dict[str, object]],
    report_number: int,
    expected_characteristics: tuple[str, ...] | None,
) -> tuple[tuple[str, ...], list[dict[str, object]]]:
    if not block_records:
        raise ValueError(f"Report {report_number} contains no valid measurement rows.")
    characteristics = tuple(str(record["Characteristic"]) for record in block_records)
    if len(set(characteristics)) != len(characteristics):
        raise ValueError(f"Report {report_number} contains a duplicated characteristic.")
    if expected_characteristics is None:
        expected_characteristics = characteristics
    elif set(characteristics) != set(expected_characteristics):
        missing = sorted(set(expected_characteristics) - set(characteristics))
        unexpected = sorted(set(characteristics) - set(expected_characteristics))
        raise ValueError(
            f"Report {report_number} has a different set of characteristics. "
            f"Missing: {missing or 'none'}; unexpected: {unexpected or 'none'}."
        )
    for record in block_records:
        record["Report"] = report_number
    return expected_characteristics, block_records


def _parse_gage_rr_blocks(lines: list[str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    block_records: list[dict[str, object]] = []
    expected_characteristics: tuple[str, ...] | None = None
    in_block = False
    block_count = 0
    for line in lines:
        if _is_gage_rr_marker(line, ":BEGIN"):
            if in_block:
                raise ValueError("Encountered a new :BEGIN marker before closing the prior report.")
            in_block = True
            block_records = []
        elif _is_gage_rr_marker(line, ":END"):
            if not in_block:
                continue
            if block_count == 0 and len(block_records) == GRR_DESIGN.report_blocks:
                records.extend(_normalize_single_dimension_measurements(block_records))
                block_count = GRR_DESIGN.report_blocks
                in_block = False
                continue
            expected_characteristics, validated = _validate_gage_rr_block(
                block_records, block_count + 1, expected_characteristics
            )
            block_count += 1
            records.extend(validated)
            in_block = False
        elif in_block:
            row = _parse_gage_rr_row(line)
            if row is not None:
                block_records.append(row)
    if in_block:
        raise ValueError("Input ended before the final :END marker.")
    if block_count == 0:
        raise ValueError("No valid BEGIN/END measurement blocks found in input file.")
    return records


def _normalize_single_dimension_measurements(
    records: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Treat one 90-row block as 90 reports for a single dimension.

    OGP exports may encode the part in the tag, for example ``C20_A001``.
    In this layout the repeated ``_A###`` suffix identifies the part, while
    the shared prefix identifies the characteristic measured in every report.
    """
    tags = [str(record["Characteristic"]) for record in records]
    match = re.fullmatch(r"(.+)_A\d+", tags[0])
    if match is None or not all(
        (current_match := re.fullmatch(r"(.+)_A\d+", tag)) is not None
        and current_match.group(1) == match.group(1)
        for tag in tags
    ):
        raise ValueError(
            "The single-block 90-measurement format requires tags such as "
            "C20_A001, C20_A002, etc., sharing one dimension prefix."
        )

    dimension = match.group(1)
    for report_number, record in enumerate(records, start=1):
        record["Report"] = report_number
        record["Characteristic"] = dimension
        record["PartTag"] = tags[report_number - 1].rsplit("_", 1)[1]
    return records


def _parse_gage_rr_continuous(lines: list[str]) -> list[dict[str, object]]:
    rows = [row for line in lines if (row := _parse_gage_rr_row(line)) is not None]
    if not rows:
        raise ValueError("No valid measurement rows found in continuous input.")
    if len(rows) == GRR_DESIGN.report_blocks:
        tags = [str(row["Characteristic"]) for row in rows]
        if all(re.fullmatch(r"(.+)_A\d+", tag) for tag in tags):
            return _normalize_single_dimension_measurements(rows)

    blocks: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    seen: set[str] = set()
    first_characteristic: str | None = None
    for row in rows:
        characteristic = str(row["Characteristic"])
        if first_characteristic is None:
            first_characteristic = characteristic
        elif characteristic == first_characteristic and current:
            blocks.append(current)
            current = []
            seen = set()
        if characteristic in seen:
            raise ValueError("Continuous data contains a duplicated characteristic before the next cycle.")
        current.append(row)
        seen.add(characteristic)
    if current:
        blocks.append(current)
    records: list[dict[str, object]] = []
    expected_characteristics: tuple[str, ...] | None = None
    for report_number, block in enumerate(blocks, start=1):
        expected_characteristics, validated = _validate_gage_rr_block(
            block, report_number, expected_characteristics
        )
        records.extend(validated)
    return records


def _parse_gage_rr_raw_data(
    input_file: _InputSource,
    input_format: str = "auto",
) -> list[dict[str, object]]:
    """Parse GRR data as explicit blocks or consecutive repeated rows."""
    if input_format not in {"auto", "blocks", "continuous"}:
        raise ValueError("input_format must be 'auto', 'blocks', or 'continuous'.")
    with _open_text_input(input_file) as fh:
        raw_text = fh.read()
    raw_text = raw_text.replace('END"":BEGIN', 'END"\n":BEGIN')
    lines = [line.lstrip("\x1a").strip() for line in raw_text.splitlines()]
    has_markers = any(
        _is_gage_rr_marker(line, ":BEGIN") or _is_gage_rr_marker(line, ":END")
        for line in lines
    )
    if input_format == "auto":
        input_format = "blocks" if has_markers else "continuous"
    return _parse_gage_rr_blocks(lines) if input_format == "blocks" else _parse_gage_rr_continuous(lines)


def _build_gage_rr_dataframe(
    records: list[dict[str, object]],
    report_order: str = "part-major",
) -> pd.DataFrame:
    """Build structured DataFrame for Gage R&R Crossed analysis.

    Assigns operators, parts, and trials to complete report blocks. For reports
    without part tags, ``report_order`` defines how sequential blocks map to
    the crossed design. Every characteristic receives the same assignment.

    Args:
        records: Parsed measurement records, including a report number.
        report_order: ``part-major`` (Part, Operator, Trial) or
            ``operator-major`` (Operator, Part, Trial) sequence.

    Returns:
        DataFrame with Part, Operator, Trial, Characteristic, Measurement, and
        characteristic-specific tolerance columns.
    """
    if report_order not in {"part-major", "operator-major"}:
        raise ValueError("report_order must be 'part-major' or 'operator-major'.")

    report_numbers = sorted({int(record["Report"]) for record in records})
    total_reports = len(report_numbers)
    if total_reports != GRR_DESIGN.report_blocks:
        raise ValueError(
            "Gage R&R requires exactly 90 report blocks: 10 parts x "
            "3 operators x 3 trials."
        )

    num_parts = GRR_DESIGN.parts
    report_positions = {report: position for position, report in enumerate(report_numbers)}
    part_tags = [str(record["PartTag"]) for record in records if "PartTag" in record]
    has_part_tags = len(part_tags) == len(records)
    if has_part_tags:
        unique_part_tags = list(dict.fromkeys(part_tags))
        if len(unique_part_tags) != GRR_DESIGN.parts:
            raise ValueError(
                f"Part-tagged Gage R&R data must contain exactly {GRR_DESIGN.parts} unique parts."
            )
        part_positions = {tag: position for position, tag in enumerate(unique_part_tags)}

    data: list[dict[str, object]] = []

    for record in records:
        report_position = report_positions[int(record["Report"])]
        if has_part_tags:
            part_num = part_positions[str(record["PartTag"])] + 1
            round_number = report_position // num_parts
            trial_num = round_number % GRR_DESIGN.trials_per_part + 1
            operator_num = round_number // GRR_DESIGN.trials_per_part + 1
        else:
            trial_num = report_position % GRR_DESIGN.trials_per_part + 1
            if report_order == "part-major":
                part_num = (
                    report_position
                    // (GRR_DESIGN.operators * GRR_DESIGN.trials_per_part)
                    + 1
                )
                operator_num = (
                    report_position // GRR_DESIGN.trials_per_part
                ) % GRR_DESIGN.operators + 1
            else:
                operator_num = (
                    report_position // (num_parts * GRR_DESIGN.trials_per_part) + 1
                )
                part_num = (
                    report_position // GRR_DESIGN.trials_per_part
                ) % num_parts + 1
        upper_tol = float(record["Upper Tol"])
        lower_tol = float(record["Lower Tol"])
        data.append(
            {
                "Report": int(record["Report"]),
                "Part": f"Part_{part_num}",
                "Operator": f"Operator_{operator_num}",
                "Trial": trial_num,
                "Characteristic": record["Characteristic"],
                "Measurement": float(record["Measurement"]),
                "Nominal": float(record["Nominal"]),
                "Upper Tol": upper_tol,
                "Lower Tol": lower_tol,
                "Tolerance": upper_tol - lower_tol,
            }
        )

    return pd.DataFrame(data)


def transform_gage_rr_data(
    input_file: _InputSource,
    output_file: Path | None = None,
    input_format: str = "auto",
    report_order: str = "part-major",
) -> pd.DataFrame:
    """Convert raw Gage R&R Crossed data into structured TSV format.

    Parses complete raw reports and preserves each measurement characteristic as
    an independent Gage R&R study. The standard 90-report study maps to 3
    operators, 10 parts, and 3 trials per part.

    Args:
        input_file: Path to raw measurement file with tolerance specs.
        output_file: Where to write resulting TSV, or ``None`` to skip.
        input_format: ``auto``, ``blocks`` for BEGIN/END reports, or
            ``continuous`` for repeated measurements without separators.
        report_order: Assignment order for untagged reports: ``part-major``
            (Part, Operator, Trial) or ``operator-major`` (Operator, Part, Trial).
    Returns:
        Structured DataFrame with columns: Part, Operator, Trial, Measurement,
        Nominal, Upper Tol, Lower Tol, Tolerance.

    Raises:
        ValueError: If input file doesn't contain exactly 90 measurements or
                    tolerance information is missing.
    """
    records = _parse_gage_rr_raw_data(input_file, input_format=input_format)
    df = _build_gage_rr_dataframe(records, report_order=report_order)

    if output_file is not None:
        df.to_csv(output_file, sep="\t", index=False)
        n_p = df['Part'].nunique()
        n_o = df['Operator'].nunique()
        n_t = df['Trial'].nunique()
        print(f"Success! Processed {df['Report'].nunique()} reports and {df['Characteristic'].nunique()} characteristics.")
        print(f"Structure: {n_p} parts x {n_t} trials x {n_o} operators")
        print(f"Data saved to '{output_file}'")

    return df


def paired_input_has_blocks(input_file: _InputSource) -> bool:
    """Return whether a paired input contains BEGIN/END report markers."""
    with _open_text_input(input_file) as fh:
        raw_text = fh.read()
    lines = [line.lstrip("\x1a").strip() for line in raw_text.splitlines()]
    return any(
        _is_paired_block_marker(line, "BEGIN") or _is_paired_block_marker(line, "END")
        for line in lines
    )


def _is_paired_block_marker(line: str, marker: str) -> bool:
    match = re.fullmatch(r'"?:?(BEGIN|END)"?(?:\t.*)?', line.strip(), re.IGNORECASE)
    return match is not None and match.group(1).casefold() == marker.lstrip(":").casefold()


def transform_paired_multicharacteristic_data(input_file: _InputSource) -> pd.DataFrame:
    """Parse paired-system report blocks into observation/characteristic rows."""
    with _open_text_input(input_file) as fh:
        raw_text = fh.read()
    raw_text = raw_text.replace('END"":BEGIN', 'END"\n":BEGIN')
    lines = [line.lstrip("\x1a").strip() for line in raw_text.splitlines()]

    records: list[dict[str, object]] = []
    block_records: list[dict[str, object]] = []
    expected_characteristics: tuple[str, ...] | None = None
    block_number = 0
    in_block = False
    found_marker = False

    for line_number, line in enumerate(lines, start=1):
        if _is_paired_block_marker(line, "BEGIN"):
            found_marker = True
            if in_block:
                raise ValueError(
                    f"Line {line_number}: a new BEGIN marker appeared before the prior block ended."
                )
            in_block = True
            block_records = []
            continue
        if _is_paired_block_marker(line, "END"):
            found_marker = True
            if not in_block:
                raise ValueError(f"Line {line_number}: END marker has no matching BEGIN.")
            if not block_records:
                raise ValueError(f"Report {block_number + 1} contains no measurement rows.")
            characteristics = tuple(str(row["Characteristic"]) for row in block_records)
            if len(set(characteristics)) != len(characteristics):
                raise ValueError(f"Report {block_number + 1} contains a duplicated characteristic.")
            if expected_characteristics is None:
                expected_characteristics = characteristics
            elif set(characteristics) != set(expected_characteristics):
                missing = sorted(set(expected_characteristics) - set(characteristics))
                unexpected = sorted(set(characteristics) - set(expected_characteristics))
                raise ValueError(
                    f"Report {block_number + 1} has a different set of characteristics. "
                    f"Missing: {missing or 'none'}; unexpected: {unexpected or 'none'}."
                )
            block_number += 1
            for row in block_records:
                records.append({"Observation": block_number, **row})
            in_block = False
            continue

        if not in_block:
            if line:
                raise ValueError(
                    f"Line {line_number}: content is not inside a BEGIN/END report block."
                )
            continue
        if not line:
            continue
        metadata_line = line.strip().strip('"')
        if metadata_line.upper().startswith(("PATTERN:", "DISPLAY:", "UNIT:")):
            continue
        if "\t" not in line:
            raise ValueError(
                f"Line {line_number}: expected a tab-separated characteristic and measurement."
            )
        parts = line.split("\t")
        characteristic = parts[0].strip().strip('"')
        if not characteristic:
            raise ValueError(f"Line {line_number}: characteristic label cannot be empty.")
        try:
            measurement = float(parts[1])
        except (ValueError, IndexError) as exc:
            raise ValueError(
                f"Line {line_number}: invalid measurement for {characteristic!r}."
            ) from exc
        if not math.isfinite(measurement):
            raise ValueError(
                f"Line {line_number}: measurement for {characteristic!r} must be finite."
            )
        block_records.append(
            {"Characteristic": characteristic, "Measurement": measurement}
        )

    if in_block:
        raise ValueError("Input ended before the final END marker.")
    if not found_marker:
        raise ValueError("No BEGIN/END measurement blocks found in paired input.")
    if block_number < 2:
        raise ValueError("Paired multi-characteristic input requires at least two report blocks.")

    return pd.DataFrame(records, columns=["Observation", "Characteristic", "Measurement"])
