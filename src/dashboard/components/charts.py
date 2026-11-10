"""Reusable charts and the click-to-filter helper."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from components.filters import SIDEBAR_DIMS, set_filter
from queries import DIMENSIONS, category_order

RISK_SCALE = ["#2e7d32", "#f9a825", "#c62828"]  # green -> amber -> red


def kpi_row(k: dict) -> None:
    cols = st.columns(5)
    cols[0].metric("Applications", fmt_compact(k["n_applications"]), help=f"{int(k['n_applications']):,}")
    cols[1].metric("Default rate", fmt_pct(k["default_rate"]))
    cols[2].metric("Median debt-to-income", fmt_num(k["median_dti"], 3))
    cols[3].metric("Overdue share", fmt_pct(k["overdue_share"]))
    cols[4].metric("Avg credit", fmt_compact(k["avg_credit"]), help=fmt_num(k["avg_credit"], 0))


def fmt_pct(v) -> str:
    return "-" if v is None or pd.isna(v) else f"{v * 100:.2f}%"


def fmt_num(v, digits: int) -> str:
    return "-" if v is None or pd.isna(v) else f"{v:,.{digits}f}"


def fmt_compact(v) -> str:
    """Large amounts for metric tiles: 36,412,345 -> 36.4M."""
    if v is None or pd.isna(v):
        return "-"
    for div, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(v) >= div:
            return f"{v / div:,.1f}{suffix}"
    return f"{v:,.0f}"


def ordered(df: pd.DataFrame, dim: str, col: str = "member") -> pd.DataFrame:
    order = category_order().get(dim)
    if not order:
        return df.sort_values("default_rate", ascending=False) if "default_rate" in df else df
    rank = {v: i for i, v in enumerate(order)}
    return df.assign(_r=df[col].map(rank).fillna(len(order))).sort_values(["_r", col]).drop(columns="_r")


def default_rate_bar(df: pd.DataFrame, dim: str, title: str | None = None, height: int = 360):
    df = ordered(df, dim)
    fig = px.bar(
        df, x="member", y="default_rate", color="default_rate",
        color_continuous_scale=RISK_SCALE, custom_data=["member"],
        hover_data={"n_applications": ":,", "n_labelled": ":,", "default_rate": ":.2%"},
        labels={"member": DIMENSIONS.get(dim, dim), "default_rate": "Default rate"},
        title=title or f"Default rate by {DIMENSIONS.get(dim, dim).lower()}",
        height=height,
    )
    fig.update_layout(coloraxis_showscale=False, yaxis_tickformat=".0%", margin=dict(t=50, b=10))
    return fig


def clicked_values(event) -> list[str]:
    points = (event or {}).get("selection", {}).get("points", []) if isinstance(event, dict) else \
        getattr(getattr(event, "selection", None), "points", []) or []
    values = []
    for p in points:
        cd = p.get("customdata")
        values.append(str(cd[0] if isinstance(cd, (list, tuple)) else cd) if cd is not None else str(p.get("x")))
    return values


def clickable(fig, dim: str, key: str) -> None:
    """Render a chart; clicking a bar becomes a sidebar filter on `dim` (if dim is a sidebar filter)."""
    if dim not in SIDEBAR_DIMS:
        st.plotly_chart(fig, width="stretch", key=key)
        return
    event = st.plotly_chart(fig, width="stretch", key=key, on_select="rerun", selection_mode="points")
    values = clicked_values(event)
    if values and sorted(values) != sorted(st.session_state.get(f"_persist_{dim}", [])):
        set_filter(dim, values)
        st.session_state.pop(key, None)  # clear the chart selection so it is not re-applied
        st.rerun()
