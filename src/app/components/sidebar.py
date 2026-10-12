from app.support import st


def render_sidebar() -> str:
    if "selected_study" not in st.session_state:
        st.session_state.selected_study = "Type 1 Gage Study"

    st.sidebar.markdown(
        """
        <div class="sidebar-title">Study Selection</div>
        <div class="sidebar-subtitle">Choose workflow</div>
        """,
        unsafe_allow_html=True,
    )

    studies = [
        ("Type 1 Gage Study", "type1_btn"),
        ("Paired T-Test", "paired_btn"),
        ("Gage R&R (Crossed)", "grr_btn"),
    ]

    for study_name, key in studies:
        is_active = (st.session_state.selected_study == study_name)
        with st.sidebar.container():
            if st.button(
                study_name,
                key=key,
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                if st.session_state.selected_study != study_name:
                    st.session_state.selected_study = study_name
                    st.rerun()

    return st.session_state.selected_study
