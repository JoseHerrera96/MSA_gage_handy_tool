import streamlit as st

from app.components.sidebar import render_sidebar
from app.theme import apply_theme
from app.views.grr_view import render_gage_rr_page
from app.views.paired_view import render_paired_page
from app.views.type1_view import render_type1_page


def main() -> None:
    apply_theme()
    study = render_sidebar()

    st.title("Integrated MSA Suite")
    st.markdown("MSA analysis with modern visual feedback and export ready dashboards.")
    st.divider()

    if study == "Type 1 Gage Study":
        render_type1_page()
    elif study == "Paired T-Test":
        render_paired_page()
    elif study == "Gage R&R (Crossed)":
        render_gage_rr_page()


if __name__ == "__main__":
    main()
