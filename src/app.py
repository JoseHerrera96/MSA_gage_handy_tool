from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any, TextIO

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gage_tracer.data_parser import transform_ogp_data
from gage_tracer.calculations import calculate_type1_metrics
from gage_tracer.visualization import create_dashboard
from gage_tracer.paired_ttest import (
    parse_paired_measurements,
    calculate_paired_ttest_metrics,
    create_paired_ttest_dashboard,
)


def _uploaded_to_textio(uploaded_file: Any) -> TextIO:
    """Convert an uploaded Streamlit file object into a reusable text stream."""
    raw = uploaded_file.read()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    return io.StringIO(raw)


def _metric_status(value: float, threshold: float) -> str:
    return "PASS" if value >= threshold else "FAIL"


def _format_type1_dataframe(summary_df: pd.DataFrame) -> pd.DataFrame:
    display_df = summary_df[
        ["Gage Item", "Reference", "Mean", "StdDev", "Bias", "T", "PValue", "Cg", "Cgk"]
    ].copy()
    display_df["PValue"] = display_df["PValue"].map("{:.6f}".format)
    display_df["Bias"] = display_df["Bias"].map("{:+.6f}".format)
    return display_df.set_index("Gage Item")


def _paired_summary_dataframe(metrics: dict[str, Any]) -> pd.DataFrame:
    return (
        pd.DataFrame(
            [
                {
                    "Metric": "N",
                    "System A": int(metrics["N"]),
                    "System B": int(metrics["N"]),
                    "Difference": "",
                },
                {
                    "Metric": "Mean",
                    "System A": f"{metrics['Mean_A']:.6f}",
                    "System B": f"{metrics['Mean_B']:.6f}",
                    "Difference": f"{metrics['Mean_D']:.6f}",
                },
                {
                    "Metric": "StDev",
                    "System A": f"{metrics['StDev_A']:.6f}",
                    "System B": f"{metrics['StDev_B']:.6f}",
                    "Difference": f"{metrics['StDev_D']:.6f}",
                },
                {
                    "Metric": "SE Mean",
                    "System A": f"{metrics['SE_A']:.6f}",
                    "System B": f"{metrics['SE_B']:.6f}",
                    "Difference": f"{metrics['SE_D']:.6f}",
                },
                {
                    "Metric": "95% CI Lower",
                    "System A": "",
                    "System B": "",
                    "Difference": f"{metrics['CI_Lower']:.6f}",
                },
                {
                    "Metric": "95% CI Upper",
                    "System A": "",
                    "System B": "",
                    "Difference": f"{metrics['CI_Upper']:.6f}",
                },
                {
                    "Metric": "T-Value",
                    "System A": "",
                    "System B": "",
                    "Difference": f"{metrics['T_Value']:.6f}",
                },
                {
                    "Metric": "Degrees of Freedom",
                    "System A": "",
                    "System B": "",
                    "Difference": int(metrics["DF"]),
                },
                {
                    "Metric": "P-Value",
                    "System A": "",
                    "System B": "",
                    "Difference": f"{metrics['P_Value']:.6f}",
                },
            ]
        )
        .set_index("Metric")
    )


def _apply_theme() -> None:
    st.set_page_config(
        page_title="Data Tracer MSA",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        :root {
            color-scheme: dark;
        }
        .stApp {
            background-color: #070B12;
            color: #F5F7FA;
        }
        .css-1d391kg, .css-1v3fvcr, .css-18ni7ap {
            background-color: #0D1622 !important;
            color: #F5F7FA !important;
        }
        .stSidebar {
            background-color: #09111E;
        }
        section[data-testid="stSidebar"] .sidebar-title {
            font-size: 1.7rem !important;
            font-weight: 900 !important;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #FFFFFF !important;
        }
        section[data-testid="stSidebar"] .sidebar-subtitle {
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            margin-bottom: 0.9rem;
            color: #D8E2FF !important;
        }
        section[data-testid="stSidebar"] .stButton>button {
            background-color: #FF4B4B !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(255, 75, 75, 0.8) !important;
            border-radius: 1rem !important;
            padding: 0.9rem 1rem !important;
            width: 100% !important;
            text-align: left !important;
            font-weight: 700 !important;
            margin-bottom: 0.6rem !important;
        }
        section[data-testid="stSidebar"] .stButton>button:hover {
            background-color: #e94444 !important;
        }
        .stButton>button, .stDownloadButton>button {
            background-color: #FF4B4B !important;
            color: #FFFFFF !important;
            border: 1px solid #FF4B4B !important;
        }
        .stButton>button:hover, .stDownloadButton>button:hover {
            background-color: #e84444 !important;
            border-color: #e84444 !important;
        }
        .stFileUploader {
            border: 1px solid #1F2A3A;
            border-radius: 1rem;
            background-color: #0E1826;
            padding: 1rem;
        }
        .stTextInput>div>div>input {
            background-color: #0E1826;
            color: #F5F7FA;
            border-color: #1F2A3A;
        }
        .stInfo, .stWarning, .stError {
            border-radius: 1rem !important;
        }
        .stDataFrame table {
            background-color: #0F1726 !important;
        }
        .stMarkdown, .stExpander {
            color: #F5F7FA;
        }
        .report-card {
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 1rem;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.03);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
            margin-bottom: 1rem;
        }
        .data-card {
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 1rem;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.02);
        }
        .section-title {
            color: #FFFFFF;
        }
        .sidebar-help li {
            margin-bottom: 0.6rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar() -> str:
    if "selected_study" not in st.session_state:
        st.session_state.selected_study = "Type 1 Gage Study"

    st.sidebar.markdown(
        """
        <div class="sidebar-title">Study selection</div>
        <div class="sidebar-subtitle">Choose workflow</div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar.container():
        if st.button("Type 1 Gage Study", key="type1_btn"):
            st.session_state.selected_study = "Type 1 Gage Study"

    with st.sidebar.container():
        if st.button("Paired T-Test", key="paired_btn"):
            st.session_state.selected_study = "Paired T-Test"

    st.sidebar.markdown(
        """
        <div class="sidebar-help">
            <ul>
                <li>Upload plain text measurement files (.txt)</li>
                <li>Export polished HTML dashboards for reporting</li>
                <li>Supports Type 1 Gage Study and Paired T-Test analysis</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return st.session_state.selected_study


def _build_type1_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    skip_cols = {"", " ", "Dimension", "Average", "Max diff", "Nominal", "Upper Tol", "Lower Tol"}
    summary: list[dict[str, Any]] = []
    for col in df.columns:
        if col.strip() not in skip_cols:
            measurements = df[col].dropna().astype(float)
            if measurements.empty:
                continue
            spec_row = df[df["Dimension"] == col].iloc[0]
            summary.append(calculate_type1_metrics(col, measurements, spec_row))
    return summary


def _render_type1_page() -> None:
    st.header("Type 1 Gage Study")
    with st.container():
        st.markdown("#### Step 1 — Upload raw OGP data")
        st.info("Upload a raw data text file to start the Type 1 Gage Study.")
        uploaded = st.file_uploader("Upload RAW DATA.txt", type=["txt"], key="type1_raw")

    st.divider()

    if uploaded is None:
        return

    try:
        with st.spinner("Processing Type 1 Gage Study data..."):
            buffer = _uploaded_to_textio(uploaded)
            df = transform_ogp_data(buffer, output_file=None)
            summary = _build_type1_summary(df)

        if not summary:
            st.error("No valid measurement dimensions were found in the uploaded file.")
            return

    except Exception as exc:
        st.error("Unable to parse the uploaded file. Please verify the input format.")
        st.warning(str(exc))
        return

    summary_df = pd.DataFrame(summary)
    pass_threshold = 1.33
    mean_cg = summary_df["Cg"].mean()
    mean_cgk = summary_df["Cgk"].mean()
    accepted = summary_df[summary_df["Status"] == "ACCEPT"].shape[0]
    total = summary_df.shape[0]
    pass_rate = f"{accepted}/{total} ({accepted * 100 / total:.0f}%)"
    cg_status = _metric_status(mean_cg, pass_threshold)
    cgk_status = _metric_status(mean_cgk, pass_threshold)

    with st.container():
        st.markdown("#### Key results")
        metrics_cols = st.columns(4)
        metrics_cols[0].metric("Dimensions", total)
        metrics_cols[1].metric("Average Cg", f"{mean_cg:.3f}", delta=cg_status)
        metrics_cols[2].metric("Average Cgk", f"{mean_cgk:.3f}", delta=cgk_status)
        metrics_cols[3].metric("Pass rate", pass_rate)

    if cg_status == "PASS" and cgk_status == "PASS":
        st.success("Cg and Cgk both meet the industrial threshold of 1.33.")
    else:
        st.warning("One or more indices fall below the minimum 1.33 threshold.")

    st.divider()

    with st.container():
        st.markdown("#### Dimension summary")
        display_df = _format_type1_dataframe(summary_df)
        st.dataframe(display_df, use_container_width=True)

    st.divider()

    with st.container():
        st.markdown("#### Export dashboard")
        html = create_dashboard(df, summary, output_path=None)
        st.download_button(
            label="Download Type 1 Dashboard HTML",
            data=html,
            file_name="Gage_Study_Summary_dashboard.html",
            mime="text/html",
        )


def _render_paired_page() -> None:
    st.header("Paired T-Test Analysis")
    with st.container():
        st.markdown("#### Step 1 — Upload paired system measurements")
        left, right = st.columns(2)
        with left:
            file_a = st.file_uploader("System A measurements", type=["txt"], key="paired_a")
        with right:
            file_b = st.file_uploader("System B measurements", type=["txt"], key="paired_b")

    st.divider()

    if file_a is None or file_b is None:
        st.info("Upload both System A and System B files to continue.")
        return

    try:
        with st.spinner("Processing paired T-Test data..."):
            buffer_a = _uploaded_to_textio(file_a)
            buffer_b = _uploaded_to_textio(file_b)
            paired_df, system_a, system_b, differences = parse_paired_measurements(buffer_a, buffer_b)
            metrics = calculate_paired_ttest_metrics(system_a, system_b)

    except ValueError as exc:
        st.error("Paired data must have the same number of observations.")
        st.warning(str(exc))
        return
    except Exception as exc:
        st.error("Unable to process the paired data files. Please verify both files are numeric and aligned.")
        st.warning(str(exc))
        return

    p_value_status = "PASS" if metrics["P_Value"] >= 0.05 else "REJECT"

    with st.container():
        st.markdown("#### Key results")
        result_cols = st.columns(4)
        result_cols[0].metric("N", int(metrics["N"]))
        result_cols[1].metric("Mean Diff", f"{metrics['Mean_D']:+.6f}")
        result_cols[2].metric("T-Statistic", f"{metrics['T_Value']:.4f}")
        result_cols[3].metric("P-Value", f"{metrics['P_Value']:.6f}", delta=p_value_status)

    if p_value_status == "PASS":
        st.success("The paired test does not reject the null hypothesis at α = 0.05.")
    else:
        st.error("The paired test rejects the null hypothesis at α = 0.05.")

    st.divider()

    with st.container():
        st.markdown("#### Paired T-Test summary")
        summary_df = _paired_summary_dataframe(metrics)
        st.dataframe(summary_df, use_container_width=True)

    st.divider()

    with st.container():
        st.markdown("#### Uploaded paired data preview")
        st.dataframe(paired_df, use_container_width=True)

    st.divider()

    with st.container():
        st.markdown("#### Export dashboard")
        html = create_paired_ttest_dashboard(paired_df, metrics, output_path=None)
        st.download_button(
            label="Download Paired T-Test Dashboard HTML",
            data=html,
            file_name="Paired_T_Test_Dashboard.html",
            mime="text/html",
        )


def main() -> None:
    _apply_theme()
    study = _render_sidebar()

    st.title("Data Tracer — Integrated MSA Suite")
    st.markdown("MSA analysis with modern visual feedback and export ready dashboards.")
    st.divider()

    if study == "Type 1 Gage Study":
        _render_type1_page()
    else:
        _render_paired_page()


if __name__ == "__main__":
    main()
