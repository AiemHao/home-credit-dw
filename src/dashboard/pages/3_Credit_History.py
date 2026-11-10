"""Credit history: bureau, days past due, previous applications, bureau trend."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from components.charts import RISK_SCALE, default_rate_bar, fmt_compact, fmt_pct, ordered
from components.page import bootstrap
from queries import (DIMENSIONS, bureau_by_type, bureau_kpis, bureau_trend, by_dimension, by_two_dimensions,
                     category_order)

filters = bootstrap("Credit History")
where, params = filters.where()

st.subheader("Credit profile of applicants vs. default")
c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(default_rate_bar(by_dimension("max_dpd_bucket", where, params), "max_dpd_bucket"),
                    width="stretch")
with c2:
    st.plotly_chart(default_rate_bar(by_dimension("bureau_active_bucket", where, params), "bureau_active_bucket"),
                    width="stretch")

c3, c4 = st.columns(2)
with c3:
    st.plotly_chart(default_rate_bar(by_dimension("prev_approval_bucket", where, params), "prev_approval_bucket"),
                    width="stretch")
with c4:
    grid = by_two_dimensions("bureau_active_bucket", "max_dpd_bucket", where, params)
    if not grid.empty:
        pivot = grid.pivot(index="y", columns="x", values="default_rate")
        order = category_order()
        pivot = pivot.reindex(index=[v for v in order["max_dpd_bucket"] if v in pivot.index],
                              columns=[v for v in order["bureau_active_bucket"] if v in pivot.columns])
        fig = px.imshow(pivot, color_continuous_scale=RISK_SCALE, text_auto=".1%", aspect="auto",
                        labels=dict(x=DIMENSIONS["bureau_active_bucket"], y=DIMENSIONS["max_dpd_bucket"],
                                    color="Default rate"),
                        title="Default rate: active bureau credits x max DPD")
        fig.update_layout(coloraxis_colorbar=dict(tickformat=".0%"))
        st.plotly_chart(fig, width="stretch")

st.subheader("Overdue share by income bracket")
od = ordered(by_dimension("income_bracket", where, params), "income_bracket")
fig = px.bar(od, x="member", y="overdue_share", labels={"member": "Income bracket", "overdue_share": "Overdue share"})
fig.update_layout(yaxis_tickformat=".0%")
st.plotly_chart(fig, width="stretch")

st.divider()
st.subheader("Credits reported by the Credit Bureau")
st.caption("From fact_bureau_credit (one row per bureau credit), restricted to the applicants selected "
           "by the sidebar filters through the shared customer dimension.")
bk = bureau_kpis(where, params)
k = st.columns(5)
k[0].metric("Bureau credits", fmt_compact(bk["n_credits"]))
k[1].metric("Applicants", fmt_compact(bk["n_customers"]), help="Applicants with at least one bureau credit")
k[2].metric("Active", fmt_pct(bk["active_share"]), help="Share of bureau credits still open")
k[3].metric("Active debt", fmt_compact(bk["active_debt"]), help="Outstanding debt on active credits")
k[4].metric("Overdue now", fmt_pct(bk["overdue_share"]), help="Share of bureau credits with days overdue > 0")

st.markdown("**Credits opened over time**")
st.caption("Dates = assumed snapshot date + DAYS_CREDIT (the dataset has only relative days).")
grain = st.radio("Grain", ["year", "quarter", "month"], index=1, horizontal=True)
trend = bureau_trend(where, params, grain)
if trend.empty:
    st.info("No bureau credits for the current filters.")
else:
    fig = px.bar(trend, x="period", y="credits_opened", color="credit_active",
                 labels={"period": grain.title(), "credits_opened": "Credits opened", "credit_active": "Status"})
    st.plotly_chart(fig, width="stretch")

types = bureau_by_type(where, params)
if not types.empty:
    fig = px.bar(types, y="credit_type", x="n_credits", color="credit_active", orientation="h",
                 labels={"credit_type": "Credit type", "n_credits": "Credits", "credit_active": "Status"},
                 title="Bureau credits by type and status")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, width="stretch")
