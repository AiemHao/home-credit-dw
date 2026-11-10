"""Common page setup: page config, warehouse check, sidebar filters."""
from __future__ import annotations

import streamlit as st

from components.filters import Filters, sidebar_filters


def bootstrap(title: str, icon: str = "📊") -> Filters:
    st.set_page_config(page_title=f"{title} · Home Credit DW", page_icon=icon, layout="wide")
    try:
        filters = sidebar_filters()
    except FileNotFoundError as exc:
        st.error(f"{exc}\n\nBuild it with `hcdw etl --source sample` (or `fixture` / `raw`).")
        st.stop()
    st.title(title)
    if filters.active:
        active = " · ".join(f"{k}: {', '.join(v)}" for k, v in filters.values.items() if v)
        st.caption(f"Filtered by {active}")
    return filters
