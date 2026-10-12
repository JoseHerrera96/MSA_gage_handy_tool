from __future__ import annotations

from app.components.alerts import show_processing_error
from app.support import (
    TYPE1_CAPABILITY_THRESHOLD,
    build_type1_summary,
    create_dashboard,
    format_type1_dataframe,
    metric_status,
    pd,
    st,
    transform_raw_data,
    uploaded_to_textio,
)


def render_type1_page() -> None:
    st.header("Type 1 Gage Study")
    with st.container():
        st.markdown("#### Step 1 — Upload raw data")
        st.info("Upload one text file containing repeated measurements of the same reference part.")
        input_format_label = st.radio(
            "How are the reports separated?",
            options=("BEGIN/END markers", "Periodic reports without markers"),
            horizontal=True,
            key="type1_input_format",
        )
        input_format = "blocks" if input_format_label == "BEGIN/END markers" else "periodic"
        if input_format == "blocks":
            st.caption(
                "One file with complete BEGIN/END report blocks. Each report "
                "must contain the same measurement characteristics."
            )
        else:
            st.caption(
                "One file with consecutive reports and no required BEGIN/END markers. "
                "Measurement rows must be tab-separated as characteristic, measurement, "
                "nominal, upper tolerance, lower tolerance. Headers and PATTERN/DISPLAY/UNIT "
                "metadata may be present. Every report must repeat the same characteristics "
                "in the same order; a repeated characteristic starts the next report."
            )
        uploaded = st.file_uploader(
            "Upload Type 1 data (.txt)",
            type=["txt"],
            key=f"type1_raw_{input_format}",
        )

    st.divider()

    if uploaded is None:
        return

    try:
        with st.spinner("Processing Type 1 Gage Study data..."):
            buffer = uploaded_to_textio(uploaded)
            df = transform_raw_data(
                buffer, output_file=None, input_format=input_format
            )
            summary = build_type1_summary(df)

        if not summary:
            st.error("No valid measurement dimensions were found in the uploaded file.")
            return

    except Exception as exc:
        show_processing_error("Unable to parse the uploaded file. Please verify the input format.", exc)
        return

    summary_df = pd.DataFrame(summary)
    observation_counts = sorted(
        int(count) for count in summary_df["Observations"].unique()
    )
    if len(observation_counts) == 1:
        st.caption(
            f"Detected {observation_counts[0]} complete measurement cycles "
            "for each characteristic."
        )
    else:
        st.warning(
            "Characteristics have different observation counts: "
            + ", ".join(map(str, observation_counts))
            + ". Check that each report contains the same characteristics."
        )
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
