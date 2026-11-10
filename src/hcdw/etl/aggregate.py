"""Aggregate: collapse the 1..N child tables to one credit profile per applicant (SQL in DuckDB)."""
from __future__ import annotations

from hcdw.db import run_sql_file, sql_files

AGG_TABLES = [
    "agg_bureau_balance",
    "agg_bureau",
    "agg_previous",
    "agg_installments",
    "agg_pos",
    "agg_cc",
    "agg_credit_profile",
]


def aggregate(con) -> dict[str, int]:
    for path in sql_files("transform", prefix="1"):
        run_sql_file(con, path)
    return {t: con.execute(f"SELECT COUNT(*) FROM staging.{t}").fetchone()[0] for t in AGG_TABLES}
