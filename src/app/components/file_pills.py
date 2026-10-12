from collections.abc import Iterable
from html import escape

import streamlit as st


def render_file_pills(labels: Iterable[str]) -> None:
    pills = [f'<span class="file-pill">{escape(label)}</span>' for label in labels]
    if pills:
        st.markdown(f'<div class="file-pills">{"".join(pills)}</div>', unsafe_allow_html=True)
