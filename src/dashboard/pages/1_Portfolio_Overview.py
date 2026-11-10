"""Portfolio overview: KPIs + risk by product and customer segments."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from components.charts import clickable, default_rate_bar, kpi_row
from components.page import bootstrap
from queries import DIMENSIONS, by_dimension, kpis, ratio_sample

filters = bootstrap("Portfolio Overview")
where, params = filters.where()
kpi_row(kpis(where, params))

c1, c2 = st.columns(2)
with c1:
    clickable(default_rate_bar(by_dimension("contract_type", where, params), "contract_type"),
              "contract_type", "ov_contract")
with c2:
    clickable(default_rate_bar(by_dimension("education_type", where, params), "education_type"),
              "education_type", "ov_education")

st.subheader("Ratios vs. default")
sample = ratio_sample(where, params)
if sample.empty:
    st.info("No labelled applications for the current filters.")
else:
    sample["outcome"] = sample["target"].map({0: "Repaid", 1: "Default"})
    c3, c4 = st.columns(2)
    with c3:
        fig = px.box(sample, x="outcome", y="debt_to_income", color="outcome", points=False,
                     color_discrete_map={"Repaid": "#2e7d32", "Default": "#c62828"},
                     title="Debt-to-income (annuity / income)")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch")
    with c4:
        fig = px.histogram(sample.dropna(subset=["ext_source_mean"]), x="ext_source_mean", color="outcome",
                           barnorm="percent", nbins=30,
                           color_discrete_map={"Repaid": "#2e7d32", "Default": "#c62828"},
                           title="External score vs. outcome share (%)")
        st.plotly_chart(fig, width="stretch")

st.subheader("Segment table")
dim = st.selectbox("Group by", list(DIMENSIONS), format_func=DIMENSIONS.get, index=list(DIMENSIONS).index("family_status"))
table = by_dimension(dim, where, params).sort_values("n_applications", ascending=False)
st.dataframe(
    table.rename(columns={"member": DIMENSIONS[dim]}),
    width="stretch", hide_index=True,
    column_config={
        "default_rate": st.column_config.NumberColumn("Default rate", format="percent"),
        "overdue_share": st.column_config.NumberColumn("Overdue share", format="percent"),
        "avg_credit": st.column_config.NumberColumn("Avg credit", format="%.0f"),
        "median_dti": st.column_config.NumberColumn("Median DTI", format="%.3f"),
    },
)
