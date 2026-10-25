from __future__ import annotations

from typing import Any

from app.components.alerts import show_processing_error
from app.components.file_pills import render_file_pills
from app.support import (
    GRR_DESIGN,
    GRR_MINIMUM_NDC,
    build_gage_rr_overview_dataframe,
    calculate_gage_rr_by_characteristic,
    classify_gage_rr,
    create_gage_rr_dashboard,
    create_gage_rr_html_dashboard,
    create_gage_rr_html_overview,
    create_gage_rr_html_zip,
    st,
    transform_gage_rr_data,
    transform_gage_rr_grouped_data,
    uploaded_to_textio,
)


def render_gage_rr_page() -> None:
    st.header("Gage R&R (Crossed) ANOVA Analysis")
    with st.container():
        st.markdown("#### Step 1 — Upload raw Gage R&R data")
        st.info("Each report block can contain multiple named characteristics. A separate Gage R&R report is calculated for every characteristic.")
        st.info(
            "Fixed crossed design: "
            f"{GRR_DESIGN.parts} parts x {GRR_DESIGN.operators} operators x "
            f"{GRR_DESIGN.trials_per_part} trials = {GRR_DESIGN.report_blocks} report blocks."
        )
        input_mode = st.radio(
            "How will you provide the reports?",
            options=(
                "One file · 90 reports",
                "10 files · one per part",
                "3 files · one per operator",
            ),
            horizontal=True,
            key="grr_input_mode",
        )
        input_format_label = st.radio(
            "How are the reports separated?",
            options=("BEGIN/END markers", "Periodic reports without markers"),
            horizontal=True,
            key="grr_input_format",
        )
        input_format = "blocks" if input_format_label == "BEGIN/END markers" else "continuous"
        if input_format == "blocks":
            st.caption(
                "Each report must have a complete BEGIN/END marker pair and the "
                "same set of measurement characteristics."
            )
        else:
            st.caption(
                "Reports must be consecutive and contain no BEGIN/END markers. "
                "Measurement rows use characteristic, measurement, nominal, "
                "upper tolerance, and lower tolerance columns; repeating the first "
                "characteristic starts the next report."
            )
        uploaded = None
        grouped_uploads: list[tuple[str, Any]] = []
        report_order = "part-major"

        if input_mode == "One file · 90 reports":
            st.caption(
                "Upload all 90 reports in one file. For untagged reports, choose "
                "how the sequence maps to parts and operators."
            )
            report_order_label = st.selectbox(
                "Untagged report sequence",
                options=("Part → Operator → Trial", "Operator → Part → Trial"),
                help=(
                    "Part → Operator → Trial: reports 1–9 are Part 1, grouped in "
                    "threes by operator. Operator → Part → Trial: reports 1–30 "
                    "are Operator 1, grouped in threes by part."
                ),
            )
            report_order = (
                "part-major" if report_order_label.startswith("Part") else "operator-major"
            )
            uploaded = st.file_uploader(
                "Upload GAGE RR DATA.txt",
                type=["txt"],
                key=f"grr_raw_{input_format}",
            )
        elif input_mode == "10 files · one per part":
            st.caption(
                "Upload 10 files, one per part. Each file must contain 9 reports: "
                "3 trials for Operator 1, then 3 for Operator 2, then 3 for Operator 3."
            )
            for part in range(1, GRR_DESIGN.parts + 1):
                part_file = st.file_uploader(
                    f"Part {part} · 9 reports",
                    type=["txt"],
                    key=f"grr_part_file_{input_format}_{part}",
                )
                grouped_uploads.append((f"Part {part}", part_file))
        else:
            st.caption(
                "Upload 3 files, one per operator. Each file must contain 30 reports: "
                "3 trials for Part 1, then 3 for Part 2, continuing through Part 10."
            )
            for operator in range(1, GRR_DESIGN.operators + 1):
                operator_file = st.file_uploader(
                    f"Operator {operator} · 30 reports",
                    type=["txt"],
                    key=f"grr_operator_file_{input_format}_{operator}",
                )
                grouped_uploads.append((f"Operator {operator}", operator_file))

    if grouped_uploads:
        render_file_pills(
            f"{label}: {file.name}"
            for label, file in grouped_uploads
            if file is not None
        )

    st.divider()

    if input_mode == "One file · 90 reports":
        if uploaded is None:
            return
    else:
        missing_groups = [label for label, file in grouped_uploads if file is None]
        if missing_groups:
            if len(missing_groups) == len(grouped_uploads):
                st.info("Upload every file for the selected Gage R&R input format.")
            else:
                st.warning(
                    "Still required: " + ", ".join(missing_groups) + "."
                )
            return

    try:
        with st.spinner("Processing Gage R&R Crossed data..."):
            if uploaded is not None:
                buffer = uploaded_to_textio(uploaded)
                df = transform_gage_rr_data(
                    buffer,
                    output_file=None,
                    input_format=input_format,
                    report_order=report_order,
                )
                upload_ids = [str(getattr(uploaded, "file_id", uploaded.name))]
            else:
                group_by = "part" if input_mode == "10 files · one per part" else "operator"
                grouped_sources = [
                    (f"{label} ({file.name})", uploaded_to_textio(file))
                    for label, file in grouped_uploads
                    if file is not None
                ]
                df = transform_gage_rr_grouped_data(
                    grouped_sources,
                    group_by=group_by,
                    input_format=input_format,
                )
                upload_ids = [
                    str(getattr(file, "file_id", file.name))
                    for _, file in grouped_uploads
                    if file is not None
                ]
            all_results = calculate_gage_rr_by_characteristic(df)

    except ValueError as exc:
        show_processing_error("Invalid data format for Gage R&R analysis.", exc)
        return
    except Exception as exc:
        show_processing_error("Unable to process the Gage R&R data file.", exc)
        return

    overview_label = "Study Overview"
    report_choice = st.selectbox(
        "Gage R&R report",
        options=[overview_label, *all_results],
        key=f"grr_report_{input_mode}_{'_'.join(upload_ids)}",
    )

    if report_choice == overview_label:
        summary = build_gage_rr_overview_dataframe(all_results)
        counts = summary["Verdict"].value_counts()
        overview_cols = st.columns(4)
        overview_cols[0].metric("Characteristics", len(summary))
        overview_cols[1].metric("Pass", int(counts.get("PASS", 0)))
        overview_cols[2].metric("Marginal", int(counts.get("MARGINAL", 0)))
        overview_cols[3].metric("Fail", int(counts.get("FAIL", 0)))
        st.caption(
            f"Study design: {GRR_DESIGN.parts} parts × {GRR_DESIGN.operators} operators × "
            f"{GRR_DESIGN.trials_per_part} trials · {df['Report'].nunique()} reports"
        )
        st.dataframe(summary, use_container_width=True, hide_index=True)

        with st.container():
            st.markdown("#### Export overview")
            overview_html = create_gage_rr_html_overview(df, all_results)
            download_cols = st.columns(2)
            download_cols[0].download_button(
                label="Download study overview HTML",
                data=overview_html,
                file_name="Gage_RR_Study_Overview.html",
                mime="text/html",
            )
            download_cols[1].download_button(
                label="Download all reports (.zip)",
                data=lambda: create_gage_rr_html_zip(df, all_results),
                file_name="Gage_RR_HTML_Reports.zip",
                mime="application/zip",
                icon=":material/archive:",
            )
            st.caption(
                "The ZIP is built on demand and may take about a minute for a full study. "
                "Keep this page open until the download starts."
            )
        return

    characteristic = report_choice
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
        download_cols = st.columns(2)
        download_cols[0].download_button(
            label="Download Gage R&R Dashboard HTML",
            data=html,
            file_name=f"Gage_RR_{characteristic}_Dashboard.html",
            mime="text/html",
        )
        download_cols[1].download_button(
            label="Download all reports (.zip)",
            data=lambda: create_gage_rr_html_zip(df, all_results),
            file_name="Gage_RR_HTML_Reports.zip",
            mime="application/zip",
            icon=":material/archive:",
        )
        st.caption(
            "The ZIP is built on demand and may take about a minute for a full study. "
            "Keep this page open until the download starts."
        )
