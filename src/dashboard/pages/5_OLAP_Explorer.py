"""OLAP query interface: build a pivot (CUBE) on the fly, or run the saved OLAP queries."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from components.charts import RISK_SCALE
from components.page import bootstrap
from queries import (DIMENSIONS, MEASURES, TOTAL, category_order, olap_files, olap_sql, pivot_cube,
                     pivot_cube_sql, run_olap)

filters = bootstrap("OLAP Explorer")
where, params = filters.where()

FORMATS = {  # measure kind -> (Streamlit column format, plotly text format)
    "percent": ("percent", ".1%"),
    "count": ("localized", ",.0f"),
    "money": ("localized", ",.0f"),
    "ratio": ("%.3f", ".3f"),
}


def _order(members: pd.Index, dim: str) -> list[str]:
    known = category_order().get(dim, [])
    body = [m for m in members if m != TOTAL]
    first = [m for m in known if m in body]
    return first + sorted(m for m in body if m not in known) + ([TOTAL] if TOTAL in members else [])


pivot_tab, saved_tab = st.tabs(["Pivot builder (CUBE)", "Saved OLAP queries"])

with pivot_tab:
    st.caption("Pick two dimensions and a measure. The query uses GROUP BY CUBE, so the 'ALL' row and "
               "column are the roll-up subtotals. Sidebar filters act as a slice/dice.")
    dims = list(DIMENSIONS)
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    row_dim = c1.selectbox("Rows", dims, index=dims.index("age_bucket"), format_func=DIMENSIONS.get)
    col_options = [d for d in dims if d != row_dim]
    col_default = "income_bracket" if row_dim != "income_bracket" else "age_bucket"
    col_dim = c2.selectbox("Columns", col_options, index=col_options.index(col_default),
                           format_func=DIMENSIONS.get)
    measure = c3.selectbox("Measure", list(MEASURES), format_func=lambda m: MEASURES[m][0])
    label, _, kind = MEASURES[measure]
    min_n = c4.number_input("Hide cells with fewer applications than", min_value=0, value=10, step=10,
                            help="Rates on tiny groups are noise; such cells are left blank.")

    long = pivot_cube(row_dim, col_dim, measure, where, params)
    if long.empty:
        st.info("No applications for the current filters.")
    else:
        long.loc[long["n_applications"] < min_n, "value"] = None
        table = long.pivot(index="row_member", columns="col_member", values="value")
        table = table.reindex(index=_order(table.index, row_dim), columns=_order(table.columns, col_dim))
        table.index.name, table.columns.name = DIMENSIONS[row_dim], DIMENSIONS[col_dim]

        col_fmt, text_fmt = FORMATS[kind]
        st.dataframe(
            table.reset_index(), width="stretch", hide_index=True,
            column_config={c: st.column_config.NumberColumn(str(c), format=col_fmt) for c in table.columns},
        )
        body = table.drop(index=TOTAL, columns=TOTAL, errors="ignore")
        if not body.empty:
            fig = px.imshow(
                body, aspect="auto", text_auto=text_fmt,
                color_continuous_scale=RISK_SCALE if kind == "percent" else "Blues",
                labels=dict(x=DIMENSIONS[col_dim], y=DIMENSIONS[row_dim], color=label),
                title=f"{label}: {DIMENSIONS[row_dim].lower()} x {DIMENSIONS[col_dim].lower()}",
            )
            if kind == "percent":
                fig.update_layout(coloraxis_colorbar=dict(tickformat=".0%"))
            st.plotly_chart(fig, width="stretch")
        csv = table.reset_index().to_csv(index=False).encode("utf-8")
        st.download_button("Download pivot (CSV)", csv, file_name=f"pivot_{row_dim}_{col_dim}_{measure}.csv",
                           mime="text/csv")
    with st.expander("SQL sent to the warehouse"):
        st.code(pivot_cube_sql(row_dim, col_dim, measure, where).strip(), language="sql")
        if params:
            st.caption(f"Parameters: {list(params)}")

with saved_tab:
    st.caption("The example queries from src/sql/olap (roll-up, cube, drill-down, slice/dice + pivot, "
               "time roll-up, ranking). They run on the whole warehouse and ignore the sidebar filters.")
    files = olap_files()
    name = st.selectbox("Query", files, format_func=lambda f: f.removesuffix(".sql").replace("_", " "))
    st.code(olap_sql(name).strip(), language="sql")
    result = run_olap(name)
    if result.empty:
        st.info("The query returned no rows (e.g. every group is below the minimum size on this dataset).")
    else:
        st.dataframe(result, width="stretch", hide_index=True)
