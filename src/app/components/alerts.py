import streamlit as st


def show_processing_error(message: str, error: Exception) -> None:
    st.error(message)
    st.warning(str(error))
