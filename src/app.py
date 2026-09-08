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

from gage_tracer.data_parser import transform_raw_data, transform_gage_rr_data
from gage_tracer.calculations import (
    calculate_gage_rr_by_characteristic,
)
from gage_tracer.visualization import create_dashboard, create_gage_rr_dashboard, create_gage_rr_html_dashboard
from gage_tracer.paired_ttest import (
    calculate_paired_ttest_diagnostics,
    parse_paired_measurements,
    calculate_paired_ttest_metrics,
    create_paired_ttest_dashboard,
)
from gage_tracer.paired_visualization import (
    create_paired_diagnostic_figures,
    create_paired_power_figure,
    create_paired_summary_figures,
    create_paired_worksheet_order_figure,
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


def _uploaded_to_textio(uploaded_file: Any) -> TextIO:
    """Convert an uploaded Streamlit file object into a reusable text stream."""
    raw = uploaded_file.read()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    return io.StringIO(raw)


def _apply_theme() -> None:
    st.set_page_config(
        page_title="Data Tracer MSA",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    theme_base = st.get_option("theme.base") or "dark"

    theme_css = """
        <style>
        :root {
            color-scheme: __COLOR_SCHEME__;
            --app-bg: #151515;
            --app-surface: #222222;
            --app-surface-raised: #2B2B2B;
            --app-border: #555555;
            --app-text: #F5F7FA;
            --app-text-muted: #C7C7C7;
            --app-accent: #FF8C00;
            --app-card-border: rgba(255, 255, 255, 0.08);
            --app-card-bg: rgba(255, 255, 255, 0.03);
            --app-shadow: rgba(0, 0, 0, 0.25);
        }
        __LIGHT_THEME_MEDIA__
        [data-baseweb="base"] {
            color-scheme: inherit;
        }
        .stApp {
            background-color: var(--app-bg) !important;
            color: var(--app-text) !important;
        }
        header[data-testid="stHeader"] {
            background-color: var(--app-surface) !important;
        }
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] > div {
            background-color: var(--app-surface) !important;
            color: var(--app-text) !important;
        }
        .stSidebar {
            background-color: var(--app-surface) !important;
        }
        section[data-testid="stSidebar"] .sidebar-title {
            font-size: 1.7rem !important;
            font-weight: 900 !important;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--app-text) !important;
        }
        section[data-testid="stSidebar"] .sidebar-subtitle {
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            margin-bottom: 0.9rem;
            color: var(--app-text-muted) !important;
        }
        section[data-testid="stSidebar"] .stButton>button {
            background-color: var(--app-accent) !important;
            color: #FFFFFF !important;
            border: 1px solid var(--app-accent) !important;
            border-radius: 1rem !important;
            padding: 0.9rem 1rem !important;
            width: 100% !important;
            text-align: left !important;
            font-weight: 700 !important;
            margin-bottom: 0.6rem !important;
        }
        section[data-testid="stSidebar"] .stButton>button:hover {
            background-color: #E07B00 !important;
        }
        .stButton>button, .stDownloadButton>button {
            background-color: var(--app-accent) !important;
            color: #FFFFFF !important;
            border: 1px solid var(--app-accent) !important;
        }
        .stButton>button:hover, .stDownloadButton>button:hover {
            background-color: #E07B00 !important;
            border-color: #E07B00 !important;
        }
        .stFileUploader {
            border: 1px solid var(--app-border);
            border-radius: 1rem;
            background-color: var(--app-surface-raised);
            padding: 1rem;
        }
        [data-testid="stFileUploader"],
        [data-testid="stFileUploaderDropzone"],
        [data-testid="stFileUploaderDropzone"] > div {
            background-color: var(--app-surface-raised) !important;
            border-color: var(--app-border) !important;
        }
        [data-testid="stFileUploader"] label,
        [data-testid="stFileUploader"] small,
        [data-testid="stFileUploader"] span,
        [data-testid="stFileUploader"] p,
        [data-testid="stFileUploader"] button {
            color: var(--app-text) !important;
        }
        [data-testid="stFileUploader"] button {
            background-color: var(--app-accent) !important;
            border: 1px solid var(--app-accent) !important;
            color: #FFFFFF !important;
        }
        [data-testid="stFileUploader"] button:hover {
            background-color: #E07B00 !important;
            border-color: #E07B00 !important;
        }
        .stTextInput input,
        .stNumberInput input,
        [data-baseweb="select"] > div {
            background-color: var(--app-surface-raised) !important;
            color: var(--app-text) !important;
            border-color: var(--app-border) !important;
        }
        .stInfo, .stWarning, .stError {
            border-radius: 1rem !important;
        }
        [data-testid="stAlert"] {
            background-color: var(--app-surface-raised) !important;
            border: 1px solid var(--app-border) !important;
            border-left-color: var(--app-border) !important;
            color: var(--app-text) !important;
        }
        [data-testid="stAlert"] > div,
        [data-testid="stAlert"] > div > div,
        [data-testid="stAlert"] [data-baseweb="notification"] {
            background-color: var(--app-surface-raised) !important;
        }
        [data-testid="stAlert"] p,
        [data-testid="stAlert"] span {
            color: var(--app-text) !important;
        }
        [data-testid="stDataFrame"],
        [data-testid="stDataFrame"] > div,
        .stDataFrame table {
            background-color: var(--app-surface) !important;
        }
        [data-testid="stDataFrame"] th,
        [data-testid="stDataFrame"] td {
            color: var(--app-text) !important;
        }
        .stMarkdown, .stExpander, [data-testid="stMarkdownContainer"] {
            color: var(--app-text) !important;
        }
        .report-card {
            border: 1px solid var(--app-card-border);
            border-radius: 1rem;
            padding: 1rem;
            background: var(--app-card-bg);
            box-shadow: 0 10px 30px var(--app-shadow);
            margin-bottom: 1rem;
        }
        .data-card {
            border: 1px solid var(--app-card-border);
            border-radius: 1rem;
            padding: 1rem;
            background: var(--app-card-bg);
        }
        .section-title {
            color: var(--app-text) !important;
        }
        .sidebar-help li {
            margin-bottom: 0.6rem;
        }
        </style>
        """.replace("__COLOR_SCHEME__", "light" if theme_base == "light" else "dark")

    if theme_base == "auto":
        theme_css = theme_css.replace(
            "__LIGHT_THEME_MEDIA__",
            """
            @media (prefers-color-scheme: light) {
                :root {
                    color-scheme: light;
                    --app-bg: #E6E6E6;
                    --app-surface: #DCDCDC;
                    --app-surface-raised: #EEEEEE;
                    --app-border: #B8B8B8;
                    --app-text: #000000;
                    --app-text-muted: #555555;
                    --app-accent: #FF8C00;
                    --app-card-border: rgba(23, 33, 43, 0.14);
                    --app-card-bg: rgba(255, 255, 255, 0.92);
                    --app-shadow: rgba(23, 33, 43, 0.10);
                }
            }
            """,
        )
    elif theme_base == "light":
        theme_css = theme_css.replace(
            "__LIGHT_THEME_MEDIA__",
            """
            :root {
                color-scheme: light;
                --app-bg: #E6E6E6;
                --app-surface: #DCDCDC;
                --app-surface-raised: #EEEEEE;
                --app-border: #B8B8B8;
                --app-text: #000000;
                --app-text-muted: #555555;
                --app-accent: #FF8C00;
                --app-card-border: rgba(23, 33, 43, 0.14);
                --app-card-bg: rgba(255, 255, 255, 0.92);
                --app-shadow: rgba(23, 33, 43, 0.10);
            }
            """,
        )
    else:
        theme_css = theme_css.replace("__LIGHT_THEME_MEDIA__", "")
    st.markdown(
        theme_css,
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

    with st.sidebar.container():
        if st.button("Gage R&R (Crossed)", key="grr_btn"):
            st.session_state.selected_study = "Gage R&R (Crossed)"

    st.sidebar.markdown(
        """
        <div class="sidebar-help">
            <ul>
                <li>Upload plain text measurement files (.txt)</li>
                <li>Export polished HTML dashboards for reporting</li>
                <li>Supports Type 1 Gage Study, Paired T-Test, and Gage R&R Crossed analysis</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return st.session_state.selected_study


def _render_type1_page() -> None:
    st.header("Type 1 Gage Study")
    with st.container():
        st.markdown("#### Step 1 — Upload raw data")
        st.info("Upload a raw data text file to start the Type 1 Gage Study.")
        uploaded = st.file_uploader("Upload RAW DATA.txt", type=["txt"], key="type1_raw")

    st.divider()

    if uploaded is None:
        return

    try:
        with st.spinner("Processing Type 1 Gage Study data..."):
            buffer = _uploaded_to_textio(uploaded)
            df = transform_raw_data(buffer, output_file=None)
            summary = build_type1_summary(df)

        if not summary:
            st.error("No valid measurement dimensions were found in the uploaded file.")
            return

    except Exception as exc:
        st.error("Unable to parse the uploaded file. Please verify the input format.")
        st.warning(str(exc))
        return

    summary_df = pd.DataFrame(summary)
    pass_threshold = TYPE1_CAPABILITY_THRESHOLD
    mean_cg = summary_df["Cg"].mean()
    mean_cgk = summary_df["Cgk"].mean()
    accepted = summary_df[summary_df["Status"] == "ACCEPT"].shape[0]
    total = summary_df.shape[0]
    pass_rate = f"{accepted}/{total} ({accepted * 100 / total:.0f}%)"
    cg_status = metric_status(mean_cg, pass_threshold)
    cgk_status = metric_status(mean_cgk, pass_threshold)

    with st.container():
        st.markdown("#### Key results")
        metrics_cols = st.columns(4)
        metrics_cols[0].metric("Dimensions", total)
        metrics_cols[1].metric("Average Cg", f"{mean_cg:.3f}", delta=cg_status)
        metrics_cols[2].metric("Average Cgk", f"{mean_cgk:.3f}", delta=cgk_status)
        metrics_cols[3].metric("Pass rate", pass_rate)

    if cg_status == "PASS" and cgk_status == "PASS":
        st.success(
            f"Cg and Cgk both meet the industrial threshold of {pass_threshold:.2f}."
        )
    else:
        st.warning(
            f"One or more indices fall below the minimum {pass_threshold:.2f} threshold."
        )

    st.divider()

    with st.container():
        st.markdown("#### Dimension summary")
        display_df = format_type1_dataframe(summary_df)
        st.dataframe(display_df, use_container_width=True)

    st.divider()

    with st.container():
        st.markdown("#### Export data")
        data_tsv = df.to_csv(sep="\t", index=False).encode("utf-8")
        st.download_button(
            label="Download gage data.txt",
            data=data_tsv,
            file_name="gage data.txt",
            mime="text/tab-separated-values",
        )

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
            diagnostics = calculate_paired_ttest_diagnostics(system_a, system_b)

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

    summary_tab, diagnostics_tab, report_card_tab = st.tabs(
        ["Summary Report", "Diagnostic Report", "Report Card"]
    )

    with summary_tab:
        gauge_figure, interval_figure = create_paired_summary_figures(metrics)
        top_left, top_right = st.columns(2)
        with top_left:
            st.pyplot(gauge_figure, use_container_width=True)
        with top_right:
            st.pyplot(interval_figure, use_container_width=True)

        bottom_left, bottom_right = st.columns(2)
        with bottom_left:
            st.markdown("#### Descriptive statistics")
            st.dataframe(paired_descriptive_dataframe(metrics), use_container_width=True, hide_index=True)
            st.caption(
                f"t = {metrics['T_Value']:.4f} | df = {metrics['DF']} | "
                f"p-value = {metrics['P_Value']:.6f}"
            )
        with bottom_right:
            st.markdown("#### Executive comments")
            conclusion = "are statistically different" if p_value_status == "REJECT" else "are not statistically different"
            st.markdown(
                f"- System A and System B {conclusion} at α = 0.05.\n"
                f"- Estimated mean difference: {metrics['Mean_D']:+.6f}.\n"
                f"- 95% confidence interval: [{metrics['CI_Lower']:+.6f}, {metrics['CI_Upper']:+.6f}]."
            )

    with diagnostics_tab:
        paired_figure, histogram_figure, run_figure = create_paired_diagnostic_figures(paired_df, metrics)
        worksheet_figure = create_paired_worksheet_order_figure(paired_df)
        power_figure = create_paired_power_figure(diagnostics)
        st.pyplot(worksheet_figure, use_container_width=True)
        diagnostic_left, diagnostic_right = st.columns(2)
        with diagnostic_left:
            st.pyplot(paired_figure, use_container_width=True)
        with diagnostic_right:
            st.pyplot(histogram_figure, use_container_width=True)
        run_left, outlier_right = st.columns(2)
        with run_left:
            st.pyplot(run_figure, use_container_width=True)
        with outlier_right:
            st.pyplot(power_figure, use_container_width=True)

        with st.container():
            st.markdown("#### Severe outliers")
            if diagnostics["Outlier_Count"]:
                st.warning(f"{diagnostics['Outlier_Count']} severe outlier(s) detected (> 3σ).")
                st.dataframe(
                    paired_outliers_dataframe(paired_df, diagnostics["Outlier_Positions"]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.success("No severe outliers detected (> 3σ).")

    with report_card_tab:
        report_columns = st.columns(3)
        report_cards = [
            ("Normality of differences", diagnostics["Normality_Status"], diagnostics["Normality_Message"]),
            ("Severe outliers", diagnostics["Outlier_Status"], f"{diagnostics['Outlier_Count']} outlier(s) detected beyond 3σ."),
            ("Sample size", diagnostics["Sample_Size_Status"], diagnostics["Sample_Size_Message"]),
        ]
        for column, (title, status, message) in zip(report_columns, report_cards):
            with column:
                if status == "PASS":
                    st.success(f"{title}\n\n{message}")
                else:
                    st.warning(f"{title}\n\n{message}")

        st.divider()
        preview_left, preview_right = st.columns([2, 1])
        with preview_left:
            st.markdown("#### Uploaded paired data")
            st.dataframe(format_paired_preview(paired_df), use_container_width=True, hide_index=True)
        with preview_right:
            st.markdown("#### Input quality")
            st.dataframe(paired_data_quality_summary(paired_df), use_container_width=True)

    st.divider()

    with st.container():
        st.markdown("#### Export data")
        data_tsv = paired_df.to_csv(sep="\t", index=False).encode("utf-8")
        st.download_button(
            label="Download paired data.txt",
            data=data_tsv,
            file_name="paired data.txt",
            mime="text/tab-separated-values",
        )

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


def _render_gage_rr_page() -> None:
    st.header("Gage R&R (Crossed) ANOVA Analysis")
    with st.container():
        st.markdown("#### Step 1 — Upload raw Gage R&R data")
        st.info("Each report block can contain multiple named characteristics. A separate Gage R&R report is calculated for every characteristic.")
        st.info(
            "Fixed crossed design: "
            f"{GRR_DESIGN.parts} parts x {GRR_DESIGN.operators} operators x "
            f"{GRR_DESIGN.trials_per_part} trials = {GRR_DESIGN.report_blocks} report blocks."
        )
        st.caption(
            "Input layout is detected automatically: BEGIN/END blocks or continuous "
            "part-tagged measurements. Headers and footers are ignored."
        )
        uploaded = st.file_uploader("Upload GAGE RR DATA.txt", type=["txt"], key="grr_raw")

    st.divider()

    if uploaded is None:
        return

    try:
        with st.spinner("Processing Gage R&R Crossed data..."):
            buffer = _uploaded_to_textio(uploaded)
            df = transform_gage_rr_data(
                buffer,
                output_file=None,
                input_format="auto",
            )
            all_results = calculate_gage_rr_by_characteristic(df)

    except ValueError as exc:
        st.error("Invalid data format for Gage R&R analysis.")
        st.warning(str(exc))
        return
    except Exception as exc:
        st.error("Unable to process the Gage R&R data file.")
        st.warning(str(exc))
        return

    characteristic = st.selectbox(
        "Characteristic report",
        options=list(all_results),
    )
    results = all_results[characteristic]
    characteristic_df = df[df["Characteristic"] == characteristic]
    st.subheader(f"Report: {characteristic}")

    # Industrial traffic light verdict
    grr_pct = results["total_grr_pct"]
    ndc = results["ndc"]

    # Determine verdict
    verdict = classify_gage_rr(grr_pct, ndc)
    if verdict == "PASS":
        verdict_color = "🟢"
        verdict_msg = "Excellent - Measurement system is acceptable"
    elif verdict == "MARGINAL":
        verdict_color = "🟡"
        verdict_msg = "Marginal - Measurement system may be acceptable depending on application"
    else:
        verdict_color = "🔴"
        verdict_msg = "Unacceptable - Measurement system needs improvement"

    with st.container():
        st.markdown("#### Key results")
        metrics_cols = st.columns(4)
        metrics_cols[0].metric("Total Gage R&R", f"{grr_pct:.2f}%")
        metrics_cols[1].metric("NDC", f"{ndc}")
        metrics_cols[2].metric("Study Variation", f"{results['study_variation']:.4f}")
        metrics_cols[3].metric("Verdict", verdict, delta=verdict_color)

    st.markdown(f"**{verdict_color} {verdict_msg}**")
    st.caption(f"Number of Distinct Categories (NDC): {ndc} | Target: >= {GRR_MINIMUM_NDC}")
    st.caption("The Number of Distinct Categories (NDC) indicates how many part-to-part categories the measurement system can reliably distinguish. A value of 5 or more is generally considered acceptable.")

    st.divider()

    with st.container():
        st.markdown("#### ANOVA Table With Interaction")
        st.dataframe(results["anova_table_with_interaction"], use_container_width=True)

    st.divider()

    with st.container():
        st.markdown("#### Final ANOVA Table")
        anova_df = results["anova_table"]
        st.dataframe(anova_df, use_container_width=True)

    st.divider()

    with st.container():
        st.markdown("#### Variance Components")
        var_df = results["variance_components"]
        st.dataframe(var_df, use_container_width=True)

    st.divider()

    with st.container():
        st.markdown("#### Gage Evaluation")
        gage_eval_df = results["gage_evaluation"]
        st.dataframe(gage_eval_df, use_container_width=True)

    st.divider()

    with st.container():
        st.markdown("#### Dashboard")
        fig = create_gage_rr_dashboard(characteristic_df, results, dark_mode=True)
        st.pyplot(fig)

    st.divider()

    with st.container():
        st.markdown("#### Pooled Interaction Status")
        if results["pooled_interaction"]:
            st.info(f"Part*Operator interaction was pooled with error (p-value = {results['interaction_p_value']:.4f} > 0.05)")
        else:
            st.warning(f"Part*Operator interaction was NOT pooled (p-value = {results['interaction_p_value']:.4f} ≤ 0.05)")

    st.divider()

    with st.container():
        st.markdown("#### Data Preview")
        st.dataframe(df, use_container_width=True)

    st.divider()

    with st.container():
        st.markdown("#### Export data")
        data_tsv = df.to_csv(sep="\t", index=False).encode("utf-8")
        st.download_button(
            label="Download gage rr data.txt",
            data=data_tsv,
            file_name="gage rr data.txt",
            mime="text/tab-separated-values",
        )

    st.divider()

    with st.container():
        st.markdown("#### Export dashboard")
        html = create_gage_rr_html_dashboard(characteristic_df, results, output_path=None)
        st.download_button(
            label="Download Gage R&R Dashboard HTML",
            data=html,
            file_name=f"Gage_RR_{characteristic}_Dashboard.html",
            mime="text/html",
        )


def main() -> None:
    _apply_theme()
    study = _render_sidebar()

    st.title("Integrated MSA Suite")
    st.markdown("MSA analysis with modern visual feedback and export ready dashboards.")
    st.divider()

    if study == "Type 1 Gage Study":
        _render_type1_page()
    elif study == "Paired T-Test":
        _render_paired_page()
    elif study == "Gage R&R (Crossed)":
        _render_gage_rr_page()


if __name__ == "__main__":
    main()
