"""gage_tracer — Measurement System Analysis package.

Public API re-exported here for convenience:

Type 1 Gage Study:
- ``transform_raw_data``: Parse raw data files into a structured TSV.
- ``calculate_type1_metrics``: Compute Cg, Cgk, bias, %Var, etc.
- ``create_dashboard``: Generate the interactive HTML dashboard.

Paired T-Test:
- ``parse_paired_measurements``: Parse two measurement files for system comparison.
- ``export_paired_data``: Export paired measurements to a structured TSV.
- ``calculate_paired_ttest_metrics``: Compute t-test statistics, p-values, CI.
- ``create_paired_ttest_dashboard``: Generate the interactive HTML dashboard.
"""

from .data_parser import transform_raw_data
from .calculations import calculate_type1_metrics
from .visualization import create_dashboard
from .paired_ttest import (
    parse_paired_measurements,
    export_paired_data,
    calculate_paired_ttest_metrics,
    create_paired_ttest_dashboard,
)

__all__ = [
    "transform_raw_data",
    "calculate_type1_metrics",
    "create_dashboard",
    "parse_paired_measurements",
    "export_paired_data",
    "calculate_paired_ttest_metrics",
    "create_paired_ttest_dashboard",
]
