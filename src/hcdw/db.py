"""Warehouse connections (local DuckDB file or MotherDuck) and SQL-file runner."""
from __future__ import annotations

import os
import re
from pathlib import Path

import duckdb

from hcdw.config import SQL_DIR, get_settings

_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def get_conn(
    target: str | None = None,
    read_only: bool = False,
    path: Path | None = None,
) -> duckdb.DuckDBPyConnection:
    """Open the warehouse.

    target: "local" (data/warehouse/hc.duckdb) or "motherduck" (md:<MD_DATABASE>).
            Defaults to DW_TARGET from .env.
    read_only: use True for the dashboard so it never blocks the ETL writer (local only).
    """
    s = get_settings()
    target = (target or s.dw_target).lower()
    if target == "local":
        p = Path(path or s.dw_path)
        if read_only and not p.exists():
            raise FileNotFoundError(f"Warehouse not found at {p}. Run `hcdw etl` first.")
        p.parent.mkdir(parents=True, exist_ok=True)
        return duckdb.connect(str(p), read_only=read_only)
    if target == "motherduck":
        if not s.motherduck_token:
            raise RuntimeError("MOTHERDUCK_TOKEN is empty. Put it in .env or use DW_TARGET=local.")
        os.environ["motherduck_token"] = s.motherduck_token
        return duckdb.connect(f"md:{s.md_database}")
    raise ValueError(f"Unknown DW_TARGET '{target}' (expected local or motherduck)")


def render_sql(text: str, params: dict[str, str] | None = None) -> str:
    params = params or {}

    def repl(m: re.Match) -> str:
        key = m.group(1)
        if key not in params:
            raise KeyError(f"SQL placeholder {{{{{key}}}}} has no value")
        return params[key]

    return _PLACEHOLDER.sub(repl, text)


def run_sql_file(con: duckdb.DuckDBPyConnection, path: Path, params: dict[str, str] | None = None) -> None:
    con.execute(render_sql(Path(path).read_text(encoding="utf-8"), params))


def sql_files(subdir: str, prefix: str = "") -> list[Path]:
    """Sorted .sql files in src/sql/<subdir>, optionally filtered by filename prefix (e.g. '2')."""
    return sorted(p for p in (SQL_DIR / subdir).glob("*.sql") if p.name.startswith(prefix))


def sql_literal_path(path: Path) -> str:
    """Quote a filesystem path for use inside a DuckDB SQL string."""
    return "'" + Path(path).resolve().as_posix().replace("'", "''") + "'"


def push_to_motherduck(local_path: Path | None = None, md_database: str | None = None) -> str:
    """Upload the local warehouse file to MotherDuck, replacing the shared database."""
    s = get_settings()
    if not s.motherduck_token:
        raise RuntimeError("MOTHERDUCK_TOKEN is empty. Put it in .env first.")
    local_path = Path(local_path or s.dw_path)
    md_database = md_database or s.md_database
    if not local_path.exists():
        raise FileNotFoundError(f"{local_path} does not exist. Run `hcdw etl` first.")
    os.environ["motherduck_token"] = s.motherduck_token
    con = duckdb.connect(str(local_path), read_only=True)
    try:
        con.execute("ATTACH 'md:'")
        con.execute(f'CREATE OR REPLACE DATABASE "{md_database}" FROM CURRENT_DATABASE()')
    finally:
        con.close()
    return md_database
