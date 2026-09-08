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

Gage R&R Crossed:
- ``transform_gage_rr_data``: Parse raw multireport files into crossed-study data.
- ``calculate_gage_rr_crossed``: Compute one crossed ANOVA study.
- ``calculate_gage_rr_by_characteristic``: Compute one study per characteristic.
- ``create_gage_rr_html_dashboard``: Generate the per-characteristic dashboard.
"""

from .data_parser import transform_raw_data, transform_gage_rr_data
from .calculations import (
    calculate_gage_rr_by_characteristic,
    calculate_gage_rr_crossed,
    calculate_type1_metrics,
)
from .visualization import create_dashboard, create_gage_rr_dashboard, create_gage_rr_html_dashboard
from .paired_ttest import (
    parse_paired_measurements,
    export_paired_data,
    calculate_paired_ttest_metrics,
    create_paired_ttest_dashboard,
)
from .study_config import (
    GRR_DESIGN,
    TYPE1_CAPABILITY_THRESHOLD,
    classify_gage_rr,
)

__all__ = [
    "transform_raw_data",
    "transform_gage_rr_data",
    "calculate_type1_metrics",
    "calculate_gage_rr_crossed",
    "calculate_gage_rr_by_characteristic",
    "create_dashboard",
    "create_gage_rr_dashboard",
    "create_gage_rr_html_dashboard",
    "parse_paired_measurements",
    "export_paired_data",
    "calculate_paired_ttest_metrics",
    "create_paired_ttest_dashboard",
    "GRR_DESIGN",
    "TYPE1_CAPABILITY_THRESHOLD",
    "classify_gage_rr",
]
