from __future__ import annotations

from pathlib import Path

from app.components.alerts import show_processing_error
from app.support import (
    build_minitab_summary_comments,
    build_paired_ttest_overview_dataframe,
    build_power_explanatory_text,
    build_report_card_rows,
    calculate_paired_ttest_diagnostics,
    calculate_paired_ttest_metrics,
    create_histogram_ci_figure,
    create_paired_slopegraph_figure,
    create_paired_ttest_dashboard,
    create_paired_ttest_html_overview,
    create_paired_ttest_html_zip,
    create_power_figure,
    create_pvalue_gauge_figure,
    create_run_chart_figure,
    create_stats_tables_figure,
    create_worksheet_order_figure,
    format_paired_preview,
    paired_data_quality_summary,
    paired_input_has_blocks,
    paired_outliers_dataframe,
    normalize_custom_report_markers,
    parse_paired_custom_measurements,
    parse_paired_measurements,
    parse_paired_multicharacteristic_measurements,
    parse_paired_unstructured_measurements,
    pd,
    st,
    uploaded_to_textio,
)


def render_paired_page() -> None:
    st.header("Paired t Test for the Mean of Two Systems")
    with st.container():
        st.markdown("#### Step 1 — Upload paired system measurements")
        st.info(
            "Upload one file for System A and one for System B. Measurements are "
            "paired by report order, so both files must contain compatible observations."
        )
        input_mode = st.radio(
            "How are the reports separated?",
            options=(
                "BEGIN/END markers",
                "Periodic reports without markers",
                "Customized",
            ),
            horizontal=True,
            key="paired_input_mode",
        )
        if input_mode == "Periodic reports without markers":
            st.caption(
                "Upload one file per system. Text-only headers/footers and BEGIN/END "
                "markers are ignored. Each measurement line must contain exactly one "
                "finite number; lines with multiple numbers or unclassified text between "
                "measurements are rejected. Values are paired by order, so both files "
                "must contain the same observations in the same order."
            )
            input_mode_key = "unstructured"
        elif input_mode == "Customized":
            marker_cols = st.columns(2)
            with marker_cols[0]:
                custom_start_marker = st.text_input(
                    "Start marker", value="BEGIN", key="paired_custom_start_marker"
                )
            with marker_cols[1]:
                custom_end_marker = st.text_input(
                    "End marker", value="END", key="paired_custom_end_marker"
                )
            st.caption(
                "Markers must occupy their own line. Use the same marker for both fields "
                "when each report is separated by one repeated delimiter. Text outside "
                "report markers is ignored."
            )
            input_mode_key = "customized"
        else:
            st.caption(
                "Upload one file per system. Use one finite number per line, or matching "
                ":BEGIN/:END blocks with tab-separated characteristic and measurement "
                "rows. Block labels must match; observations pair by block order."
            )
            input_mode_key = "structured"
        left, right = st.columns(2)
        with left:
            file_a = st.file_uploader(
                "System A measurements",
                type=["txt"],
                key=f"paired_a_{input_mode_key}",
            )
        with right:
            file_b = st.file_uploader(
                "System B measurements",
                type=["txt"],
                key=f"paired_b_{input_mode_key}",
            )

    st.divider()

    if file_a is None or file_b is None:
        st.info("Upload both System A and System B files to continue.")
        return

    try:
        with st.spinner("Processing paired T-Test data..."):
            selected_characteristic: str | None = None
            system_a_name = Path(file_a.name).stem if hasattr(file_a, "name") else "System A"
            system_b_name = Path(file_b.name).stem if hasattr(file_b, "name") else "System B"
            if "PAIRED DATA " in system_a_name:
                system_a_name = system_a_name.replace("PAIRED DATA ", "")
            if "PAIRED DATA " in system_b_name:
                system_b_name = system_b_name.replace("PAIRED DATA ", "")

            if input_mode == "Customized":
                normalized_a = normalize_custom_report_markers(
                    uploaded_to_textio(file_a),
                    custom_start_marker,
                    custom_end_marker,
                    source_name=system_a_name,
                )
                normalized_b = normalize_custom_report_markers(
                    uploaded_to_textio(file_b),
                    custom_start_marker,
                    custom_end_marker,
                    source_name=system_b_name,
                )
                analyses = parse_paired_custom_measurements(
                    normalized_a, normalized_b
                )
            elif input_mode == "Periodic reports without markers":
                buffer_a = uploaded_to_textio(file_a)
                buffer_b = uploaded_to_textio(file_b)
                paired_df, system_a, system_b, differences = (
                    parse_paired_unstructured_measurements(buffer_a, buffer_b)
                )
                metrics = calculate_paired_ttest_metrics(system_a, system_b)
                diagnostics = calculate_paired_ttest_diagnostics(
                    system_a,
                    system_b,
                    system_a_name=system_a_name,
                    system_b_name=system_b_name,
                )
            else:
                has_blocks_a = paired_input_has_blocks(uploaded_to_textio(file_a))
                has_blocks_b = paired_input_has_blocks(uploaded_to_textio(file_b))
                if has_blocks_a != has_blocks_b:
                    raise ValueError("Both systems must use the same paired input format.")

                if has_blocks_a:
                    analyses = parse_paired_multicharacteristic_measurements(
                        uploaded_to_textio(file_a), uploaded_to_textio(file_b)
                    )
                else:
                    analyses = None

            if input_mode == "Customized" or (
                input_mode != "Periodic reports without markers" and analyses is not None
            ):
                for analysis in analyses.values():
                    analysis["metrics"] = calculate_paired_ttest_metrics(
                        analysis["system_a"], analysis["system_b"]
                    )
                    analysis["diagnostics"] = calculate_paired_ttest_diagnostics(
                        analysis["system_a"],
                        analysis["system_b"],
                        system_a_name=system_a_name,
                        system_b_name=system_b_name,
                    )
                numeric_series_key = "__custom_numeric_series__"
                is_custom_numeric_series = (
                    input_mode == "Customized"
                    and list(analyses) == [numeric_series_key]
                )
                if is_custom_numeric_series:
                    selected_report = numeric_series_key
                else:
                    overview = build_paired_ttest_overview_dataframe(analyses)
                    overview_label = "Study Overview"
                    selected_report = st.selectbox(
                        "Paired T-Test report",
                        options=[overview_label, *analyses],
                        key=f"paired_report_{file_a.file_id}_{file_b.file_id}",
                    )
                    if selected_report == overview_label:
                        holm_values = overview["Holm P-Value"]
                        overview_cols = st.columns(3)
                        overview_cols[0].metric("Characteristics", len(overview))
                        overview_cols[1].metric(
                            "Significant after Holm", int((holm_values < 0.05).sum())
                        )
                        overview_cols[2].metric(
                            "With diagnostic warnings",
                            int(
                                (
                                    (overview["Outlier Status"] != "PASS")
                                    | (overview["Normality"] != "PASS")
                                ).sum()
                            ),
                        )
                        st.dataframe(overview, use_container_width=True, hide_index=True)
                        st.caption(
                            "Holm-adjusted p-values account for testing multiple characteristics. "
                            "No significant difference detected is not evidence that the systems are equivalent."
                        )
                        with st.container():
                            st.markdown("#### Export overview")
                            overview_html = create_paired_ttest_html_overview(
                                overview, system_a_name, system_b_name
                            )
                            download_cols = st.columns(2)
                            download_cols[0].download_button(
                                label="Download study overview HTML",
                                data=overview_html,
                                file_name="Paired_T_Test_Study_Overview.html",
                                mime="text/html",
                            )
                            download_cols[1].download_button(
                                label="Download all reports (.zip)",
                                data=lambda: create_paired_ttest_html_zip(
                                    analyses, system_a_name, system_b_name
                                ),
                                file_name="Paired_T_Test_HTML_Reports.zip",
                                mime="application/zip",
                                icon=":material/archive:",
                            )
                            st.caption(
                                "The ZIP is built on demand. Keep this page open until the download starts."
                            )
                        return

                selected_analysis = analyses[selected_report]
                paired_df = selected_analysis["paired_df"]
                system_a = selected_analysis["system_a"]
                system_b = selected_analysis["system_b"]
                differences = selected_analysis["differences"]
                metrics = selected_analysis["metrics"]
                diagnostics = selected_analysis["diagnostics"]
                if not is_custom_numeric_series:
                    selected_characteristic = selected_report
                    st.subheader(f"Characteristic: {selected_report}")
            elif input_mode != "Periodic reports without markers":
                buffer_a = uploaded_to_textio(file_a)
                buffer_b = uploaded_to_textio(file_b)
                paired_df, system_a, system_b, differences = parse_paired_measurements(
                    buffer_a, buffer_b
                )
                metrics = calculate_paired_ttest_metrics(system_a, system_b)
                diagnostics = calculate_paired_ttest_diagnostics(
                    system_a,
                    system_b,
                    system_a_name=system_a_name,
                    system_b_name=system_b_name,
                )

    except ValueError as exc:
        show_processing_error("Unable to align paired data. Verify the selected input format and observation order.", exc)
        return
    except Exception as exc:
        show_processing_error("Unable to process the paired data files. Please verify both files are numeric and aligned.", exc)
        return

    p_value = float(metrics["P_Value"])
    p_value_label = f"{p_value:.6f}"
    alpha_comparison = f"p {'<' if p_value < 0.05 else '>'} 0.05"

    with st.expander("Paired observations preview", expanded=False):
        st.dataframe(paired_df.head(10), use_container_width=True, hide_index=True)
        if len(paired_df) > 10:
            st.caption(f"Showing the first 10 of {len(paired_df)} paired observations.")
        if input_mode in {"Periodic reports without markers", "Customized"}:
            st.caption("Source line columns identify the original measurement row in each file.")

    with st.container():
        st.markdown("#### Key results")
        result_cols = st.columns(4)
        result_cols[0].metric("Sample size", int(metrics["N"]))
        result_cols[1].metric("Mean difference", f"{float(metrics['Mean_D']):+.6g}")
        result_cols[2].metric("T-Statistic", f"{float(metrics['T_Value']):.4f}")
        result_cols[3].metric("P-Value", p_value_label)

    if p_value < 0.05:
        st.success(
            f"The mean of {system_a_name} is significantly different from the mean of {system_b_name} ({alpha_comparison})."
        )
    else:
        st.info(
            f"The mean of {system_a_name} is not significantly different from the mean of {system_b_name} ({alpha_comparison})."
        )

    st.divider()

    summary_tab, diagnostics_tab, report_card_tab = st.tabs(
        ["Summary Report", "Diagnostic Report", "Report Card"]
    )

    with summary_tab:
        gauge_figure = create_pvalue_gauge_figure(metrics, system_a_name=system_a_name, system_b_name=system_b_name)
        stats_tables_figure = create_stats_tables_figure(metrics, system_a_name=system_a_name, system_b_name=system_b_name)
        histogram_ci_figure = create_histogram_ci_figure(paired_df, metrics)
        top_left, top_right = st.columns(2)
        with top_left:
            st.pyplot(gauge_figure, use_container_width=True)
        with top_right:
            st.pyplot(stats_tables_figure, use_container_width=True)

        bottom_left, bottom_right = st.columns(2)
        with bottom_left:
            st.pyplot(histogram_ci_figure, use_container_width=True)
        with bottom_right:
            st.markdown("#### Comments")
            comments = build_minitab_summary_comments(metrics)
            for comment in comments:
                body = comment["body"]
                heading = comment["heading"]
                if body.startswith(f"{heading}:"):
                    body_text = body[len(heading) + 1:].lstrip()
                elif body.startswith(f"{heading} "):
                    body_text = body[len(heading) + 1:].lstrip()
                else:
                    body_text = body
                st.markdown(f"**{heading}:** {body_text}")

    with diagnostics_tab:
        outlier_positions = list(diagnostics["Outlier_Positions"])
        worksheet_figure = create_worksheet_order_figure(
            paired_df, outlier_positions, system_a_name=system_a_name, system_b_name=system_b_name
        )
        slopegraph_figure = create_paired_slopegraph_figure(
            paired_df, metrics, system_a_name=system_a_name, system_b_name=system_b_name
        )
        run_figure = create_run_chart_figure(paired_df, metrics)
        power_figure = create_power_figure(diagnostics, metrics)

        _, chart_area, _ = st.columns([0.075, 0.85, 0.075])
        with chart_area:
            st.pyplot(worksheet_figure, use_container_width=True)
            diag_left, diag_right = st.columns(2)
            with diag_left:
                st.pyplot(slopegraph_figure, use_container_width=True)
            with diag_right:
                st.pyplot(run_figure, use_container_width=True)
            st.pyplot(power_figure, use_container_width=True)

        power_text = build_power_explanatory_text(diagnostics)
        st.caption(power_text["paragraph"])
        st.info(power_text["footer"])

        with st.container():
            st.markdown("#### Severe outlier summary (> 3σ)")
            if diagnostics["Outlier_Count"]:
                st.warning(f"{int(diagnostics['Outlier_Count'])} severe outlier(s) detected (> 3σ).")
                st.dataframe(
                    paired_outliers_dataframe(paired_df, diagnostics["Outlier_Positions"]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.success("No severe outliers detected (> 3σ).")

    with report_card_tab:
        st.markdown("#### Report Card")
        report_rows = build_report_card_rows(metrics, diagnostics)
        report_df = pd.DataFrame(
            {
                "Check": [r["Check"] for r in report_rows],
                "Status": [r["Icon"] for r in report_rows],
                "Description": [r["Description"] for r in report_rows],
            }
        )
        st.dataframe(
            report_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.TextColumn("Status", width="small"),
            },
        )

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
        html = create_paired_ttest_dashboard(
            paired_df,
            metrics,
            output_path=None,
            system_a_name=system_a_name,
            system_b_name=system_b_name,
            characteristic_name=selected_characteristic,
        )
        st.download_button(
            label="Download Paired T-Test Dashboard HTML",
            data=html,
            file_name="Paired_T_Test_Dashboard.html",
            mime="text/html",
        )
