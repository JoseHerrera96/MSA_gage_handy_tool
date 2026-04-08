"""
OGP output data transformation module:

This module reads OGP measurement data from a text file, parses dimension measurements, and exports 
them to a TSV file with computed statistics (average and max difference) interleaved with measurement 
data for each dimension.
"""

import pandas as pd


def _parse_ogp_data(input_file: str) -> tuple[list[dict[str, float]], dict[str, dict[str, float]]]:

    """
    Parse raw OGP data file into measurement repetitions and specs.

    Reads dimension measurement blocks delimited by ':BEGIN' and ':END' markers. Extracts 
    dimension names, values, and tolerance specs. Stores nominal, upper tolerance, and lower 
    tolerance per dimension.

    Args:
        input_file: Path to the OGP raw data file.

    Returns:
        Tuple of (measurements list, specs dict).
        measurements: List of dicts with dimension names and measured values.
        specs: Dict mapping dimension names to their nominal, upper, lower tolerance values (extracted 
        from first occurrence).
    """
    all_repetitions: list[dict[str, float]] = []
    current_repetition: dict[str, float] = {}
    dimension_specs: dict[str, dict[str, float]] = {}

    with open(input_file, 'r') as file:
        for line in file:
            line = line.strip()

            if line.startswith('":BEGIN"'):
                current_repetition = {}
            elif line.startswith('":END"'):
                if current_repetition:
                    all_repetitions.append(current_repetition)
            elif line.startswith('"C'):                 #change to accepted dimension that do not start with "C" if needed
                parts = line.split('\t')
                if len(parts) >= 5:
                    raw_dim_name = parts[0].strip('"')
                    dim_name = raw_dim_name.replace('_OUT1', '')            #change to only remove specific suffix if is present, to avoid removing valid characters from dimension names
                    try:
                        measurement = float(parts[1])
                        nominal = float(parts[2])
                        upper_tol = float(parts[3])
                        lower_tol = float(parts[4])

                        current_repetition[dim_name] = measurement

                        # Store specs from first occurrence
                        if dim_name not in dimension_specs:
                            dimension_specs[dim_name] = {
                                'nominal': nominal,
                                'upper_tol': upper_tol,
                                'lower_tol': lower_tol,
                            }
                    except ValueError:
                        continue

    return all_repetitions, dimension_specs


def _compute_dimension_statistics(df: pd.DataFrame,specs: dict[str, dict[str, float]],) -> pd.DataFrame:

    """
    Compute average and max difference for each dimension column.

    Args:
        df: DataFrame with measurement columns.
        specs: Dictionary with nominal and tolerance values per dimension.

    Returns:
        DataFrame with columns: 'Dimension', 'Average', 'Max diff',
        'Nominal', 'Upper Tol', 'Lower Tol'.
    """
    stats = []
    for dim in df.columns:
        spec = specs.get(dim, {
            'nominal': '',
            'upper_tol': '',
            'lower_tol': '',
        })
        stats.append({
            'Dimension': dim,
            'Average': df[dim].mean(),
            'Max diff': df[dim].max() - df[dim].min(),
            'Nominal': spec['nominal'],
            'Upper Tol': spec['upper_tol'],
            'Lower Tol': spec['lower_tol'],
        })
    return pd.DataFrame(stats)


def _build_interleaved_output(df: pd.DataFrame, stats_df: pd.DataFrame,) -> pd.DataFrame:

    """
    Create output with data section, separators, and vertical stats.

    Structure: [measurement columns] + [2 blank columns] + [stats lookup].
    Stats section: Dimension | Average | Max diff | Nominal | Upper Tol | Lower Tol 
    (vertical, one per row)

    Args:
        df: DataFrame with measurement data.
        stats_df: DataFrame with pre-computed statistics and specs.

    Returns:
        Combined DataFrame with data section and vertical stats section.
    """
    combined_df = df.copy()

    # Add 2 separator columns
    combined_df[''] = ''
    combined_df[' '] = ''

    # Add the stats section columns with object dtype
    for col in ('Dimension', 'Average', 'Max diff','Nominal', 'Upper Tol', 'Lower Tol'):
        combined_df[col] = pd.Series(dtype='object', index=combined_df.index)

    # Fill stats rows
    for idx, row in stats_df.iterrows():
        combined_df.loc[idx, 'Dimension'] = row['Dimension']
        combined_df.loc[idx, 'Average'] = row['Average']
        combined_df.loc[idx, 'Max diff'] = row['Max diff']
        combined_df.loc[idx, 'Nominal'] = row['Nominal']
        combined_df.loc[idx, 'Upper Tol'] = row['Upper Tol']
        combined_df.loc[idx, 'Lower Tol'] = row['Lower Tol']

    return combined_df


def _format_output_dataframe(df: pd.DataFrame,) -> pd.DataFrame:

    """
    Format numeric columns to specified decimal precision.

    Measurement columns: 7 decimals.
    Average, Max diff, Nominal, Upper Tol, Lower Tol: 8 decimals.
    Separator and Dimension columns: left as-is.

    Args:
        df: DataFrame with mixed numeric data.

    Returns:
        DataFrame with all numeric values formatted as strings.
    """
    for col in df.columns:
        if col in ('', ' ', 'Dimension'):
            # Keep separator and dimension columns unchanged
            continue
        elif col in (
            'Average', 'Max diff', 'Nominal',
            'Upper Tol', 'Lower Tol'
        ):
            def format_stats(x: float | str) -> str:
                """Format value to 8 decimals if non-empty."""
                if pd.isna(x) or (isinstance(x, str) and x == ''):
                    return ''
                return f'{float(x):.8f}'
            df[col] = df[col].apply(format_stats)
        else:
            def format_measurement(x: float | str) -> str:
                """Format value to 7 decimals if non-empty."""
                if pd.isna(x) or (isinstance(x, str) and x == ''):
                    return ''
                return f'{float(x):.7f}'
            df[col] = df[col].apply(format_measurement)
    return df


def transform_ogp_data(input_file: str,output_file: str,) -> None:
    
    """
    Transform OGP data file into structured measurement output.

    Reads raw OGP measurements, computes statistics per dimension,
    and exports results to TSV format with interleaved data/stats.

    Args:
        input_file: Path to input OGP raw data file.
        output_file: Path to output TSV file.
    """
    all_repetitions, specs = _parse_ogp_data(input_file)
    df = pd.DataFrame(all_repetitions)
    stats_df = _compute_dimension_statistics(df, specs)
    combined_df = _build_interleaved_output(df, stats_df)
    combined_df = _format_output_dataframe(combined_df)

    combined_df.to_csv(output_file, sep='\t', index=False)

    print(f"Success! Processed {len(all_repetitions)} repetitions.")
    print(
        f"Detected {len(df.columns)} unique dimensions: "
        f"{', '.join(df.columns)}"
    )
    print(f"Data saved to '{output_file}'")


if __name__ == '__main__':
    INPUT_FILE = 'OGP DATA.txt'
    OUTPUT_FILE = 'gage data.txt'

    transform_ogp_data(INPUT_FILE, OUTPUT_FILE)