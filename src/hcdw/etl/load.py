"""Load: rebuild dw (dimensions, then facts) and mart views from staging."""
from __future__ import annotations

from hcdw.config import SQL_DIR, Settings
from hcdw.db import run_sql_file, sql_files

DW_TABLES = [
    "dim_time",
    "dim_customer",
    "dim_credit_history",
    "dim_contract",
    "dim_region",
    "dim_bureau_category",
    "fact_loan_application",
    "fact_bureau_credit",
]


def load(con, settings: Settings) -> dict[str, int]:
    params = settings.sql_params
    # Full refresh: the source is a static snapshot, so drop and rebuild.
    con.execute("DROP SCHEMA IF EXISTS mart CASCADE")
    con.execute("DROP SCHEMA IF EXISTS dw CASCADE")
    run_sql_file(con, SQL_DIR / "ddl" / "00_schemas.sql")
    run_sql_file(con, SQL_DIR / "ddl" / "02_dimensions.sql", params)
    run_sql_file(con, SQL_DIR / "ddl" / "03_facts.sql", params)

    for prefix in ("2", "3"):  # 2x = dimensions, 3x = facts
        for path in sql_files("transform", prefix=prefix):
            run_sql_file(con, path, params)
    build_marts(con, settings)
    return {t: con.execute(f"SELECT COUNT(*) FROM dw.{t}").fetchone()[0] for t in DW_TABLES}


def build_marts(con, settings: Settings) -> None:
    for path in sql_files("marts"):
        run_sql_file(con, path, settings.sql_params)
