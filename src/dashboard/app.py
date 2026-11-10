"""Home Credit DSS dashboard - entry point.

Run from the repo root:  streamlit run src/dashboard/app.py
Pages live in src/dashboard/pages/ (Streamlit multipage).
"""
from __future__ import annotations

import streamlit as st

from components.charts import clickable, default_rate_bar, kpi_row
from components.page import bootstrap
from hcdw.config import get_settings
from queries import by_dimension, kpis

filters = bootstrap("Home Credit - Credit Risk Data Warehouse")
s = get_settings()
st.caption(
    f"Warehouse: **{s.dw_target}** "
    + (f"(`{s.dw_path.name}`)" if s.dw_target == "local" else f"(MotherDuck `{s.md_database}`)")
    + " · default rate uses labelled (train) applications only"
)

where, params = filters.where()
kpi_row(kpis(where, params))

left, right = st.columns(2)
with left:
    clickable(default_rate_bar(by_dimension("age_bucket", where, params), "age_bucket"), "age_bucket", "home_age")
with right:
    clickable(default_rate_bar(by_dimension("income_type", where, params), "income_type"), "income_type",
              "home_income_type")

st.markdown(
    """
**Pages**
- **Portfolio Overview** - KPIs and risk by contract, education, ratios
- **Demographic Drilldown** - age → income → employment → occupation, click a bar to drill
- **Credit History** - days past due, previous applications, bureau credits by type and over time
- **Risk Simulator** - DSS scoring with Green / Yellow / Red decision
- **OLAP Explorer** - build any pivot (CUBE with subtotals) and run the saved OLAP queries

"""
)
