"""Every SQL statement the dashboard runs lives here (OLAP layer of the web app).

Rules that keep this safe and fast:
  * Dimension and measure names are whitelisted (DIMENSIONS / MEASURES) before they are formatted
    into SQL; member values always travel as bound parameters.
  * Filters are a hashable tuple, so every query is memoised with lru_cache: the warehouse is a
    static snapshot, so a result never goes stale until the ETL rebuilds the file (restart the API).
  * One read-only DuckDB connection, one cursor per query (cursors are cheap and thread-safe to
    create; the connection object itself must not be shared across threads).
"""
from __future__ import annotations

import json
import threading
from functools import lru_cache
from pathlib import Path

import duckdb
import pandas as pd

from hcdw.config import SQL_DIR, get_settings
from hcdw.db import get_conn

APP_VIEW = "mart.v_application_wide"
BUREAU_VIEW = "mart.v_bureau_credit_wide"
TOTAL = "ALL"

# Columns the UI may group or filter by.
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
FILTER_DIMS = ["age_bucket", "income_bracket", "income_type", "gender", "contract_type", "education_type"]

# label, SQL expression, display kind
MEASURES: dict[str, tuple[str, str, str]] = {
    "default_rate": ("Default rate", "AVG(target) FILTER (WHERE is_train)", "percent"),
    "n_applications": ("Applications", "COUNT(*)", "count"),
    "overdue_share": ("Overdue share", "AVG(overdue_flag::INTEGER)", "percent"),
    "avg_credit": ("Avg credit", "AVG(amt_credit)", "money"),
    "total_credit": ("Total credit", "SUM(amt_credit)", "money"),
    "median_dti": ("Median debt-to-income", "MEDIAN(debt_to_income)", "ratio"),
    "avg_ext_source": ("Avg external score", "AVG(ext_source_mean)", "ratio"),
}

Filters = tuple[tuple[str, tuple[str, ...]], ...]


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


def check_dim(dim: str) -> str:
    if dim not in DIMENSIONS:
        raise ValueError(f"Unknown dimension '{dim}'")
    return dim


def make_filters(raw: dict[str, list[str]]) -> Filters:
    """Normalise {dim: [members]} into a sorted, hashable tuple (unknown dims are rejected)."""
    return tuple(sorted((check_dim(d), tuple(sorted(set(v)))) for d, v in raw.items() if v))


def where(filters: Filters, extra: str | None = None) -> tuple[str, tuple]:
    clauses, params = [], []
    for dim, values in filters:
        clauses.append(f"{check_dim(dim)} IN ({', '.join('?' for _ in values)})")
        params.extend(values)
    if extra:
        clauses.append(extra)
    return ("WHERE " + " AND ".join(clauses) if clauses else ""), tuple(params)


class Warehouse:
    """Lazily opened read-only connection to the warehouse."""

    def __init__(self, dw_path: Path | None = None) -> None:
        self.dw_path = dw_path
        self._con: duckdb.DuckDBPyConnection | None = None
        self._lock = threading.Lock()

    def connection(self) -> duckdb.DuckDBPyConnection:
        with self._lock:
            if self._con is None:
                s = get_settings()
                if self.dw_path is not None:
                    self._con = get_conn("local", read_only=True, path=self.dw_path)
                else:
                    self._con = get_conn(read_only=s.dw_target == "local")
            return self._con

    def df(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        return self.connection().cursor().execute(sql, list(params)).df()

    def close(self) -> None:
        with self._lock:
            if self._con is not None:
                self._con.close()
                self._con = None


def records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-safe records (NaN -> null, numpy scalars -> Python, dates -> ISO)."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def row(df: pd.DataFrame) -> dict:
    out = records(df)
    return out[0] if out else {}


class Queries:
    """All dashboard queries, memoised per (filters, args)."""

    def __init__(self, wh: Warehouse) -> None:
        self.wh = wh
        # lru_cache on bound methods would pin `self`; wrap per instance instead.
        for name in ("members", "kpis", "by_dimension", "cross", "score_curve", "dti_by_outcome",
                     "hierarchy", "bureau_kpis", "bureau_trend", "bureau_by_type", "pivot", "run_olap",
                     "warehouse_info"):
            setattr(self, name, lru_cache(maxsize=512)(getattr(self, name)))

    # ---- metadata -----------------------------------------------------------------------------
    def members(self, dim: str) -> list[str]:
        check_dim(dim)
        values = self.wh.df(f"SELECT DISTINCT {dim} AS v FROM {APP_VIEW} WHERE {dim} IS NOT NULL")["v"]
        values = [str(v) for v in values]
        order = category_order().get(dim)
        if order:
            return [v for v in order if v in values] + sorted(v for v in values if v not in order)
        return sorted(values)

    def warehouse_info(self) -> dict:
        counts = self.wh.df("""
            SELECT schema_name, table_name, estimated_size AS n_rows
            FROM duckdb_tables() WHERE schema_name = 'dw' ORDER BY table_name""")
        return {"tables": records(counts)}

    # ---- application fact ---------------------------------------------------------------------
    def kpis(self, filters: Filters) -> dict:
        w, p = where(filters)
        return row(self.wh.df(f"""
            SELECT
                COUNT(*)                                AS n_applications,
                COUNT(*) FILTER (WHERE is_train)        AS n_labelled,
                AVG(target) FILTER (WHERE is_train)     AS default_rate,
                MEDIAN(debt_to_income)                  AS median_dti,
                AVG(overdue_flag::INTEGER)              AS overdue_share,
                AVG(amt_credit)                         AS avg_credit,
                SUM(amt_credit)                         AS total_credit,
                AVG(ext_source_mean)                    AS avg_ext_source
            FROM {APP_VIEW} {w}""", p))

    def by_dimension(self, dim: str, filters: Filters) -> list[dict]:
        check_dim(dim)
        w, p = where(filters)
        df = self.wh.df(f"""
            SELECT
                CAST({dim} AS VARCHAR)                  AS member,
                COUNT(*)                                AS n_applications,
                COUNT(*) FILTER (WHERE is_train)        AS n_labelled,
                AVG(target) FILTER (WHERE is_train)     AS default_rate,
                AVG(overdue_flag::INTEGER)              AS overdue_share,
                AVG(amt_credit)                         AS avg_credit,
                MEDIAN(debt_to_income)                  AS median_dti
            FROM {APP_VIEW} {w}
            GROUP BY 1""", p)
        return records(_ordered(df, dim))

    def cross(self, dim_x: str, dim_y: str, filters: Filters) -> list[dict]:
        check_dim(dim_x), check_dim(dim_y)
        w, p = where(filters)
        return records(self.wh.df(f"""
            SELECT CAST({dim_x} AS VARCHAR) AS x, CAST({dim_y} AS VARCHAR) AS y,
                   COUNT(*) FILTER (WHERE is_train)    AS n_labelled,
                   AVG(target) FILTER (WHERE is_train) AS default_rate
            FROM {APP_VIEW} {w}
            GROUP BY ALL""", p))

    def score_curve(self, filters: Filters, bins: int = 20) -> list[dict]:
        """Default rate per external-score bin (labelled rows): the risk curve of EXT_SOURCE."""
        w, p = where(filters, "is_train AND ext_source_mean IS NOT NULL")
        n = int(bins)
        return records(self.wh.df(f"""
            SELECT
                LEAST(FLOOR(ext_source_mean * {n}), {n - 1})::INTEGER   AS bin,
                (LEAST(FLOOR(ext_source_mean * {n}), {n - 1}) + 0.5) / {n} AS score_mid,
                COUNT(*)                                                  AS n_labelled,
                AVG(target)                                               AS default_rate
            FROM {APP_VIEW} {w}
            GROUP BY ALL ORDER BY bin""", p))

    def dti_by_outcome(self, filters: Filters) -> list[dict]:
        """Five-number summary of debt-to-income for repaid vs defaulted loans (exact, no sample)."""
        w, p = where(filters, "is_train AND debt_to_income IS NOT NULL")
        return records(self.wh.df(f"""
            SELECT
                CASE WHEN target = 1 THEN 'Default' ELSE 'Repaid' END AS outcome,
                COUNT(*)                                 AS n,
                QUANTILE_CONT(debt_to_income, 0.05)      AS p05,
                QUANTILE_CONT(debt_to_income, 0.25)      AS p25,
                QUANTILE_CONT(debt_to_income, 0.50)      AS p50,
                QUANTILE_CONT(debt_to_income, 0.75)      AS p75,
                QUANTILE_CONT(debt_to_income, 0.95)      AS p95
            FROM {APP_VIEW} {w}
            GROUP BY 1 ORDER BY 1 DESC""", p))

    def hierarchy(self, levels: tuple[str, ...], filters: Filters) -> list[dict]:
        for d in levels:
            check_dim(d)
        cols = ", ".join(f"CAST({d} AS VARCHAR) AS {d}" for d in levels)
        w, p = where(filters)
        return records(self.wh.df(f"""
            SELECT {cols},
                   COUNT(*)                            AS n_applications,
                   AVG(target) FILTER (WHERE is_train) AS default_rate
            FROM {APP_VIEW} {w}
            GROUP BY ALL""", p))

    # ---- bureau fact (drill-across through dim_customer) --------------------------------------
    def _bureau_scope(self, filters: Filters) -> tuple[str, tuple]:
        if not filters:
            return "", ()
        w, p = where(filters)
        return f"WHERE customer_key IN (SELECT customer_key FROM {APP_VIEW} {w})", p

    def bureau_kpis(self, filters: Filters) -> dict:
        w, p = self._bureau_scope(filters)
        return row(self.wh.df(f"""
            SELECT
                COUNT(*)                                                       AS n_credits,
                COUNT(DISTINCT customer_key)                                   AS n_customers,
                AVG((credit_active = 'Active')::INTEGER)                       AS active_share,
                SUM(amt_credit_sum_debt) FILTER (WHERE credit_active = 'Active') AS active_debt,
                AVG((credit_day_overdue > 0)::INTEGER)                         AS overdue_share,
                MEDIAN(credit_duration_days)                                   AS median_duration_days
            FROM {BUREAU_VIEW} {w}""", p))

    def bureau_trend(self, filters: Filters, grain: str = "quarter") -> list[dict]:
        period = {
            "month": "year_month",
            "quarter": "year || '-Q' || quarter",
            "year": "CAST(year AS VARCHAR)",
        }[grain]
        w, p = self._bureau_scope(filters)
        return records(self.wh.df(f"""
            SELECT {period} AS period, credit_active,
                   COUNT(*) AS credits_opened,
                   SUM(amt_credit_sum) AS credit_sum
            FROM {BUREAU_VIEW} {w}
            GROUP BY ALL
            ORDER BY period""", p))

    def bureau_by_type(self, filters: Filters, top: int = 6) -> list[dict]:
        w, p = self._bureau_scope(filters)
        return records(self.wh.df(f"""
            WITH b AS (SELECT * FROM {BUREAU_VIEW} {w}),
            top_types AS (SELECT credit_type FROM b GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT {int(top)})
            SELECT CASE WHEN credit_type IN (SELECT credit_type FROM top_types) THEN credit_type
                        ELSE 'Other' END AS credit_type,
                   credit_active,
                   COUNT(*) AS n_credits
            FROM b
            GROUP BY ALL
            ORDER BY n_credits DESC""", p))

    # ---- OLAP explorer ------------------------------------------------------------------------
    @staticmethod
    def pivot_sql(row_dim: str, col_dim: str, measure: str, where_sql: str) -> str:
        check_dim(row_dim), check_dim(col_dim)
        if row_dim == col_dim:
            raise ValueError("Rows and columns must be different dimensions")
        if measure not in MEASURES:
            raise ValueError(f"Unknown measure '{measure}'")
        expr = MEASURES[measure][1]
        return f"""SELECT
    CASE WHEN GROUPING({row_dim}) = 1 THEN '{TOTAL}' ELSE CAST({row_dim} AS VARCHAR) END AS row_member,
    CASE WHEN GROUPING({col_dim}) = 1 THEN '{TOTAL}' ELSE CAST({col_dim} AS VARCHAR) END AS col_member,
    {expr} AS value,
    COUNT(*) AS n_applications
FROM {APP_VIEW} {where_sql}
GROUP BY CUBE ({row_dim}, {col_dim})"""

    def pivot(self, row_dim: str, col_dim: str, measure: str, filters: Filters) -> dict:
        w, p = where(filters)
        sql = self.pivot_sql(row_dim, col_dim, measure, w)
        cells = records(self.wh.df(sql, p))
        rows = self._axis(row_dim, {c["row_member"] for c in cells})
        cols = self._axis(col_dim, {c["col_member"] for c in cells})
        return {"sql": sql, "params": list(p), "rows": rows, "cols": cols, "cells": cells}

    def _axis(self, dim: str, members: set[str]) -> list[str]:
        body = [m for m in members if m != TOTAL]
        known = category_order().get(dim, [])
        ordered = [m for m in known if m in body] + sorted(m for m in body if m not in known)
        return ordered + ([TOTAL] if TOTAL in members else [])

    @staticmethod
    def olap_files() -> list[str]:
        return [p.name for p in sorted((SQL_DIR / "olap").glob("*.sql"))]

    @classmethod
    def olap_sql(cls, name: str) -> str:
        if name not in cls.olap_files():  # never a user-supplied path
            raise ValueError(f"Unknown OLAP query '{name}'")
        return (SQL_DIR / "olap" / name).read_text(encoding="utf-8")

    def run_olap(self, name: str) -> dict:
        df = self.wh.df(self.olap_sql(name))
        return {"columns": [str(c) for c in df.columns], "rows": records(df)}


def _ordered(df: pd.DataFrame, dim: str) -> pd.DataFrame:
    order = category_order().get(dim)
    if not order:
        return df.sort_values("n_applications", ascending=False)
    rank = {v: i for i, v in enumerate(order)}
    return (df.assign(_r=df["member"].map(rank).fillna(len(order)))
              .sort_values(["_r", "member"]).drop(columns="_r"))
