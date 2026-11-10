"""Extract: Kaggle CSV files -> staging.* tables.

Every staging table is declared in src/sql/ddl/01_staging.sql. For each declared column we look
for a CSV column of the same name (case-insensitive) and TRY_CAST it to the declared type; a
column missing from the file is loaded as NULL. Reading with all_varchar avoids type-sniffing
errors on the 27M-row files.
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from hcdw.config import SQL_DIR
from hcdw.db import run_sql_file, sql_literal_path

log = logging.getLogger(__name__)

# staging table -> source file stems (Kaggle names). application gets train + test.
SOURCES: dict[str, list[str]] = {
    "application": ["application_train", "application_test"],
    "bureau": ["bureau"],
    "bureau_balance": ["bureau_balance"],
    "previous_application": ["previous_application"],
    "installments_payments": ["installments_payments"],
    "pos_cash_balance": ["POS_CASH_balance"],
    "credit_card_balance": ["credit_card_balance"],
}
REQUIRED = {"application_train"}


def find_source_file(source_dir: Path, stem: str) -> Path | None:
    """Find <stem>.csv or <stem>.csv.gz in source_dir (case-insensitive)."""
    wanted = {f"{stem}.csv".lower(), f"{stem}.csv.gz".lower()}
    for p in sorted(Path(source_dir).iterdir()):
        if p.is_file() and p.name.lower() in wanted:
            return p
    return None


def _staging_columns(con: duckdb.DuckDBPyConnection, table: str) -> list[tuple[str, str]]:
    return con.execute(
        """
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema = 'staging' AND table_name = ?
        ORDER BY ordinal_position
        """,
        [table],
    ).fetchall()


def _csv_header(con: duckdb.DuckDBPyConnection, path: Path) -> dict[str, str]:
    rows = con.execute(
        f"DESCRIBE SELECT * FROM read_csv({sql_literal_path(path)}, header = true, all_varchar = true)"
    ).fetchall()
    return {r[0].lower(): r[0] for r in rows}


def load_file(con: duckdb.DuckDBPyConnection, table: str, path: Path, is_train: bool | None = None) -> int:
    header = _csv_header(con, path)
    exprs = []
    for col, dtype in _staging_columns(con, table):
        if col == "is_train":
            exprs.append(f"{'TRUE' if is_train else 'FALSE'} AS is_train")
        elif col in header:
            exprs.append(f'TRY_CAST("{header[col]}" AS {dtype}) AS {col}')
        else:
            exprs.append(f"CAST(NULL AS {dtype}) AS {col}")
    before = con.execute(f"SELECT COUNT(*) FROM staging.{table}").fetchone()[0]
    con.execute(
        f"INSERT INTO staging.{table} SELECT {', '.join(exprs)} "
        f"FROM read_csv({sql_literal_path(path)}, header = true, all_varchar = true)"
    )
    after = con.execute(f"SELECT COUNT(*) FROM staging.{table}").fetchone()[0]
    return after - before


def extract(con: duckdb.DuckDBPyConnection, source_dir: Path) -> dict[str, int]:
    """(Re)create staging tables and load every source file. Returns rows loaded per file."""
    source_dir = Path(source_dir)
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Source folder not found: {source_dir}")
    run_sql_file(con, SQL_DIR / "ddl" / "00_schemas.sql")
    run_sql_file(con, SQL_DIR / "ddl" / "01_staging.sql")

    counts: dict[str, int] = {}
    for table, stems in SOURCES.items():
        for stem in stems:
            path = find_source_file(source_dir, stem)
            if path is None:
                if stem in REQUIRED:
                    raise FileNotFoundError(f"{stem}.csv not found in {source_dir}")
                log.warning("%s not found in %s - staging.%s gets no rows from it", stem, source_dir, table)
                continue
            is_train = (stem == "application_train") if table == "application" else None
            counts[stem] = load_file(con, table, path, is_train=is_train)
            log.info("extract %-24s -> staging.%-22s %10d rows", path.name, table, counts[stem])
    return counts
