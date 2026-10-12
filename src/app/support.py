from __future__ import annotations

import io
from pathlib import Path
from typing import Any, TextIO

import pandas as pd
import streamlit as st

from gage_tracer.data_parser import transform_raw_data, transform_gage_rr_data
from gage_tracer.data_parser import paired_input_has_blocks
from gage_tracer.data_parser import transform_gage_rr_grouped_data
from gage_tracer.calculations import (
    calculate_gage_rr_by_characteristic,
)
from gage_tracer.visualization import (
    build_gage_rr_overview_dataframe,
    create_dashboard,
    create_gage_rr_dashboard,
    create_gage_rr_html_dashboard,
    create_gage_rr_html_overview,
    create_gage_rr_html_zip,
)
from gage_tracer.paired_ttest import (
    build_minitab_summary_comments,
    build_power_explanatory_text,
    build_report_card_rows,
    build_paired_ttest_overview_dataframe,
    calculate_paired_ttest_diagnostics,
    create_paired_ttest_html_overview,
    create_paired_ttest_html_zip,
    parse_paired_multicharacteristic_measurements,
    parse_paired_measurements,
    parse_paired_unstructured_measurements,
    calculate_paired_ttest_metrics,
    create_paired_ttest_dashboard,
)
from gage_tracer.paired_visualization import (
    create_histogram_ci_figure,
    create_power_figure,
    create_paired_slopegraph_figure,
    create_pvalue_gauge_figure,
    create_run_chart_figure,
    create_stats_tables_figure,
    create_worksheet_order_figure,
)
from gage_tracer.study_config import (
    GRR_DESIGN,
    GRR_MINIMUM_NDC,
    TYPE1_CAPABILITY_THRESHOLD,
    classify_gage_rr,
)
from gage_tracer.presentation import (
    build_type1_summary,
    format_paired_preview,
    format_type1_dataframe,
    metric_status,
    paired_data_quality_summary,
    paired_descriptive_dataframe,
    paired_outliers_dataframe,
    paired_summary_dataframe,
)

def uploaded_to_textio(uploaded_file: Any) -> TextIO:
    """Convert an uploaded Streamlit file object into a reusable text stream."""
    raw = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    return io.StringIO(raw)
