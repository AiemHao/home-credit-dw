"""All dashboard SQL lives here.

Pages never write SQL themselves: they call these functions with a Filters object, which keeps the
queries reviewable in one place and lets Streamlit cache every result.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from hcdw.config import SQL_DIR, get_settings
from hcdw.db import get_conn

APP_VIEW = "mart.v_application_wide"
BUREAU_VIEW = "mart.v_bureau_credit_wide"

# Columns the UI may group or filter by (whitelist -> safe to format into SQL).
DIMENSIONS: dict[str, str] = {
    "age_bucket": "Age bucket",
    "income_bracket": "Income bracket",
    "income_type": "Employment type",
    "occupation_type": "Occupation",
    "education_type": "Education",
    "family_status": "Family status",
    "gender": "Gender",
    "contract_type": "Contract type",
    "housing_type": "Housing",
    "bureau_active_bucket": "Active bureau credits",
    "max_dpd_bucket": "Max days past due",
    "prev_approval_bucket": "Previous approval rate",
    "population_density_band": "Region density",
    "appr_weekday": "Application weekday",
}

# Measures the pivot explorer may aggregate (whitelist: label, SQL expression, display format).
MEASURES: dict[str, tuple[str, str, str]] = {
    "default_rate": ("Default rate", "AVG(target) FILTER (WHERE is_train)", "percent"),
    "n_applications": ("Applications", "COUNT(*)", "count"),
    "overdue_share": ("Overdue share", "AVG(overdue_flag::INTEGER)", "percent"),
    "avg_credit": ("Avg credit", "AVG(amt_credit)", "money"),
    "total_credit": ("Total credit", "SUM(amt_credit)", "money"),
    "median_dti": ("Median debt-to-income", "MEDIAN(debt_to_income)", "ratio"),
    "avg_ext_source": ("Avg external score", "AVG(ext_source_mean)", "ratio"),
}
TOTAL = "ALL"


def category_order() -> dict[str, list[str]]:
    s = get_settings()
    return {
        "age_bucket": s.bucket("age_years")[1] + ["Unknown"],
        "income_bracket": s.bucket("income")[1] + ["Unknown"],
        "max_dpd_bucket": ["No DPD", "1-30", "31-60", "61-90", "90+"],
        "bureau_active_bucket": ["No bureau record", "0", "1-2", "3-5", "6+"],
        "prev_approval_bucket": ["No previous", "No decision", "<50%", "50-99%", "100%"],
        "population_density_band": ["Low", "Medium", "High", "Unknown"],
        "appr_weekday": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"],
    }


@st.cache_resource(show_spinner=False)
def _connection():
    s = get_settings()
    return get_conn(read_only=s.dw_target == "local")


def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    # A cursor per query: DuckDB connections must not be shared across Streamlit threads.
    return _connection().cursor().execute(sql, list(params)).df()


def _check_dim(dim: str) -> str:
    if dim not in DIMENSIONS:
        raise ValueError(f"Unknown dimension {dim}")
    return dim


@st.cache_data(show_spinner=False)
def distinct_values(dim: str) -> list[str]:
    _check_dim(dim)
    df = query(f"SELECT DISTINCT {dim} AS v FROM {APP_VIEW} WHERE {dim} IS NOT NULL")
    values = df["v"].astype(str).tolist()
    order = category_order().get(dim)
    if order:
        return [v for v in order if v in values] + sorted(v for v in values if v not in order)
    return sorted(values)


@st.cache_data(show_spinner=False)
def kpis(where: str, params: tuple) -> dict:
    df = query(f"""
        SELECT
            COUNT(*)                                     AS n_applications,
            COUNT(*) FILTER (WHERE is_train)             AS n_labelled,
            AVG(target) FILTER (WHERE is_train)          AS default_rate,
            MEDIAN(debt_to_income)                       AS median_dti,
            AVG(overdue_flag::INTEGER)                   AS overdue_share,
            AVG(amt_credit)                              AS avg_credit,
            SUM(amt_credit)                              AS total_credit
        FROM {APP_VIEW} {where}""", params)
    return df.iloc[0].to_dict()


@st.cache_data(show_spinner=False)
def by_dimension(dim: str, where: str, params: tuple) -> pd.DataFrame:
    _check_dim(dim)
    return query(f"""
        SELECT
            {dim}                                        AS member,
            COUNT(*)                                     AS n_applications,
            COUNT(*) FILTER (WHERE is_train)             AS n_labelled,
            AVG(target) FILTER (WHERE is_train)          AS default_rate,
            AVG(overdue_flag::INTEGER)                   AS overdue_share,
            AVG(amt_credit)                              AS avg_credit,
            MEDIAN(debt_to_income)                       AS median_dti
        FROM {APP_VIEW} {where}
        GROUP BY {dim}""", params)


@st.cache_data(show_spinner=False)
def by_two_dimensions(dim_x: str, dim_y: str, where: str, params: tuple) -> pd.DataFrame:
    _check_dim(dim_x), _check_dim(dim_y)
    return query(f"""
        SELECT {dim_x} AS x, {dim_y} AS y,
               COUNT(*) FILTER (WHERE is_train)    AS n_labelled,
               AVG(target) FILTER (WHERE is_train) AS default_rate
        FROM {APP_VIEW} {where}
        GROUP BY ALL""", params)


@st.cache_data(show_spinner=False)
def hierarchy(levels: tuple[str, ...], where: str, params: tuple) -> pd.DataFrame:
    for d in levels:
        _check_dim(d)
    cols = ", ".join(levels)
    return query(f"""
        SELECT {cols},
               COUNT(*)                            AS n_applications,
               AVG(target) FILTER (WHERE is_train) AS default_rate
        FROM {APP_VIEW} {where}
        GROUP BY {cols}""", params)


@st.cache_data(show_spinner=False)
def ratio_sample(where: str, params: tuple, n: int = 30000) -> pd.DataFrame:
    """Row-level sample for distributions (labelled rows only).

    DuckDB applies USING SAMPLE before WHERE, so the filter runs in a subquery first; otherwise a
    narrow filter would only see the matching rows that happened to land in the sample.
    """
    extra = ("AND" if where else "WHERE") + " is_train"
    return query(f"""
        SELECT * FROM (
            SELECT credit_to_income, debt_to_income, ext_source_mean, target
            FROM {APP_VIEW} {where} {extra}
        ) USING SAMPLE reservoir({int(n)} ROWS) REPEATABLE (42)""", params)


def _bureau_scope(where: str) -> str:
    """Restrict bureau credits to the applicants selected by the sidebar filters (drill-across
    through the shared customer dimension). No filter -> no subquery."""
    if not where:
        return ""
    return f"WHERE customer_key IN (SELECT customer_key FROM {APP_VIEW} {where})"


@st.cache_data(show_spinner=False)
def bureau_trend(where: str, params: tuple, grain: str = "quarter") -> pd.DataFrame:
    period = {"month": "year_month", "quarter": "year || '-Q' || quarter", "year": "CAST(year AS VARCHAR)"}[grain]
    return query(f"""
        SELECT {period} AS period, credit_active,
               COUNT(*) AS credits_opened,
               SUM(amt_credit_sum) AS credit_sum
        FROM {BUREAU_VIEW} {_bureau_scope(where)}
        GROUP BY ALL
        ORDER BY period""", params)


@st.cache_data(show_spinner=False)
def bureau_kpis(where: str, params: tuple) -> dict:
    df = query(f"""
        SELECT
            COUNT(*)                                                     AS n_credits,
            COUNT(DISTINCT customer_key)                                 AS n_customers,
            AVG((credit_active = 'Active')::INTEGER)                     AS active_share,
            SUM(amt_credit_sum_debt) FILTER (WHERE credit_active = 'Active') AS active_debt,
            AVG((credit_day_overdue > 0)::INTEGER)                       AS overdue_share,
            MEDIAN(credit_duration_days)                                 AS median_duration_days
        FROM {BUREAU_VIEW} {_bureau_scope(where)}""", params)
    return df.iloc[0].to_dict()


@st.cache_data(show_spinner=False)
def bureau_by_type(where: str, params: tuple, top: int = 8) -> pd.DataFrame:
    """Credits per credit type x status; rare types are folded into 'Other'."""
    return query(f"""
        WITH b AS (SELECT * FROM {BUREAU_VIEW} {_bureau_scope(where)}),
        top_types AS (SELECT credit_type FROM b GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT {int(top)})
        SELECT CASE WHEN credit_type IN (SELECT credit_type FROM top_types) THEN credit_type ELSE 'Other' END
                   AS credit_type,
               credit_active,
               COUNT(*) AS n_credits
        FROM b
        GROUP BY ALL
        ORDER BY n_credits DESC""", params)


def pivot_cube_sql(row_dim: str, col_dim: str, measure: str, where: str) -> str:
    """SQL for one measure over row_dim x col_dim with CUBE subtotals (labelled 'ALL'), long format."""
    _check_dim(row_dim), _check_dim(col_dim)
    if row_dim == col_dim:
        raise ValueError("Rows and columns must be different dimensions")
    if measure not in MEASURES:
        raise ValueError(f"Unknown measure {measure}")
    expr = MEASURES[measure][1]
    return f"""
        SELECT
            CASE WHEN GROUPING({row_dim}) = 1 THEN '{TOTAL}' ELSE CAST({row_dim} AS VARCHAR) END AS row_member,
            CASE WHEN GROUPING({col_dim}) = 1 THEN '{TOTAL}' ELSE CAST({col_dim} AS VARCHAR) END AS col_member,
            {expr}   AS value,
            COUNT(*) AS n_applications
        FROM {APP_VIEW} {where}
        GROUP BY CUBE ({row_dim}, {col_dim})"""


@st.cache_data(show_spinner=False)
def pivot_cube(row_dim: str, col_dim: str, measure: str, where: str, params: tuple) -> pd.DataFrame:
    return query(pivot_cube_sql(row_dim, col_dim, measure, where), params)


def olap_files() -> list[str]:
    """Saved OLAP queries in src/sql/olap (also used in the report)."""
    return [p.name for p in sorted((SQL_DIR / "olap").glob("*.sql"))]


def olap_sql(name: str) -> str:
    if name not in olap_files():  # only files from the folder, never a user-supplied path
        raise ValueError(f"Unknown OLAP query {name}")
    return (SQL_DIR / "olap" / name).read_text(encoding="utf-8")


@st.cache_data(show_spinner=False)
def run_olap(name: str) -> pd.DataFrame:
    return query(olap_sql(name))
