from pathlib import Path

import streamlit as st

_AUTO_LIGHT_THEME = """
            @media (prefers-color-scheme: light) {
                :root {
                    color-scheme: light;
                    --bg-main: #F9FAFB;
                    --bg-sidebar: #F3F4F6;
                    --surface-card: #FFFFFF;
                    --brand-orange: #F58220;
                    --brand-orange-hover: rgba(245, 130, 32, 0.08);
                    --text-primary: #111827;
                    --text-secondary: #4B5563;
                    --border-color: #E5E7EB;
                    --error-bg: rgba(239, 68, 68, 0.08);
                    --error-border: #EF4444;
                    --error-text: #B91C1C;
                    --app-shadow: rgba(0, 0, 0, 0.08);
                }
            }
            
"""
_STATIC_LIGHT_THEME = """
            :root {
                color-scheme: light;
                --bg-main: #F9FAFB;
                --bg-sidebar: #F3F4F6;
                --surface-card: #FFFFFF;
                --brand-orange: #F58220;
                --brand-orange-hover: rgba(245, 130, 32, 0.08);
                --text-primary: #111827;
                --text-secondary: #4B5563;
                --border-color: #E5E7EB;
                --error-bg: rgba(239, 68, 68, 0.08);
                --error-border: #EF4444;
                --error-text: #B91C1C;
                --app-shadow: rgba(0, 0, 0, 0.08);
            }
            
"""


def apply_theme() -> None:
    st.set_page_config(
        page_title="Data Tracer MSA",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    theme_base = st.get_option("theme.base") or "dark"
    theme_css = (Path(__file__).parent / "assets" / "styles.css").read_text(encoding="utf-8")
    theme_css = theme_css.replace(
        "__COLOR_SCHEME__", "light" if theme_base == "light" else "dark"
    )
    if theme_base == "auto":
        theme_css = theme_css.replace("__LIGHT_THEME_MEDIA__", _AUTO_LIGHT_THEME)
    elif theme_base == "light":
        theme_css = theme_css.replace("__LIGHT_THEME_MEDIA__", _STATIC_LIGHT_THEME)
    else:
        theme_css = theme_css.replace("__LIGHT_THEME_MEDIA__", "")
    st.markdown(theme_css, unsafe_allow_html=True)
