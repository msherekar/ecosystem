# src/interface/layout.py

import streamlit as st


def layout_columns():
    """
    Defines the main layout: left (center panel) and right (chat panel).
    Adjust the column ratios to balance space.
    """
    data_col, chat_col = st.columns([2.5, 1], gap="medium")
    return data_col, chat_col


def layout_containers():
    """
    Alternative layout using containers instead of columns.
    Can be useful when vertical stacking is preferred.
    """
    center_panel = st.container(border=True)
    chat_panel = st.container(border=True)
    return center_panel, chat_panel


def layout_sidebar_header():
    """
    Optional: Displays a consistent sidebar title/logo/header.
    """
    st.sidebar.button("Select Modules", use_container_width= True)


def layout_sidebar_spacer(lines=10):
    """
    Inserts vertical space in the sidebar to push controls downward.
    """
    for _ in range(lines):
        st.sidebar.write("")
