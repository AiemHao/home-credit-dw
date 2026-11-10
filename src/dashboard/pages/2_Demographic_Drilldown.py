"""Drill-down along a customer hierarchy (OLAP drill-down / roll-up).

Click a bar to drill one level down; use the breadcrumb buttons to roll back up.
"""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from components.charts import RISK_SCALE, clicked_values, default_rate_bar
from components.page import bootstrap
from queries import DIMENSIONS, by_dimension, hierarchy

filters = bootstrap("Demographic Drill-down")

DEFAULT_PATH = ["age_bucket", "income_bracket", "income_type", "occupation_type"]
CANDIDATES = ["age_bucket", "income_bracket", "income_type", "occupation_type", "education_type",
              "family_status", "gender", "housing_type"]

path = st.multiselect("Hierarchy (drill order)", CANDIDATES, default=DEFAULT_PATH,
                      format_func=DIMENSIONS.get, max_selections=5)
if len(path) < 2:
    st.warning("Pick at least two levels.")
    st.stop()

# Reset the drill state whenever the hierarchy changes.
if st.session_state.get("_drill_path_dims") != path:
    st.session_state["_drill_path_dims"] = path
    st.session_state["_drill_members"] = []
members: list[str] = st.session_state["_drill_members"]

# Breadcrumb: All > 25-34 > 150k-200k ...
crumbs = st.columns(len(path) + 1)
if crumbs[0].button("All", width="stretch"):
    st.session_state["_drill_members"] = []
    st.rerun()
for i, m in enumerate(members):
    if crumbs[i + 1].button(f"› {m}", help=f"{DIMENSIONS[path[i]]} = {m}", width="stretch"):
        st.session_state["_drill_members"] = members[: i + 1]
        st.rerun()

level = len(members)
drill = {path[i]: members[i] for i in range(level)}
where, params = filters.where(**drill)

if level < len(path):
    dim = path[level]
    df = by_dimension(dim, where, params)
    st.caption(f"Level {level + 1}/{len(path)} - click a bar to drill into it")
    event = st.plotly_chart(default_rate_bar(df, dim, height=420), width="stretch",
                            key=f"drill_{level}", on_select="rerun", selection_mode="points")
    clicked = clicked_values(event)
    if clicked:
        st.session_state["_drill_members"] = members + [clicked[0]]
        st.session_state.pop(f"drill_{level}", None)
        st.rerun()
    st.dataframe(df.sort_values("n_applications", ascending=False), width="stretch", hide_index=True,
                 column_config={"default_rate": st.column_config.NumberColumn("Default rate", format="percent"),
                                "overdue_share": st.column_config.NumberColumn("Overdue", format="percent")})
else:
    st.success("Lowest level reached. Use the breadcrumb to roll up.")

st.subheader("Whole hierarchy")
levels = tuple(path[:3])
h = hierarchy(levels, *filters.where())
if not h.empty:
    fig = px.sunburst(h, path=list(levels), values="n_applications", color="default_rate",
                      color_continuous_scale=RISK_SCALE, height=560,
                      hover_data={"default_rate": ":.2%"})
    fig.update_layout(margin=dict(t=10, b=10), coloraxis_colorbar=dict(tickformat=".0%", title="Default"))
    st.plotly_chart(fig, width="stretch")
