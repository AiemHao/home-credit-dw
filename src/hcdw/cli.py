"""Command line: `hcdw <command>` (or `python -m hcdw <command>`)."""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import typer

from hcdw.config import SQL_DIR, get_settings

app = typer.Typer(add_completion=False, help="Home Credit DW: download, sample, ETL, quality, OLAP, push.")


@app.callback()
def _main(verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug logging")) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )


def _resolve_source(source: str) -> Path:
    s = get_settings()
    named = {"raw": s.raw_dir, "sample": s.sample_dir, "fixture": s.fixture_dir}
    return named.get(source, Path(source))


@app.command()
def download() -> None:
    """Download the Kaggle competition files into data/raw.

    Needs the competition rules accepted on kaggle.com and a Kaggle credential: KAGGLE_API_TOKEN
    (new KGAT_ tokens; may be set in .env) or ~/.kaggle/kaggle.json (legacy)."""
    s = get_settings()  # also loads .env, so KAGGLE_API_TOKEN there reaches the kaggle CLI
    # The venv's Scripts folder is not on PATH unless the venv is activated.
    kaggle = shutil.which("kaggle") or shutil.which("kaggle", path=str(Path(sys.executable).parent))
    if kaggle is None:
        typer.echo('kaggle CLI not found. Run: pip install -e ".[etl]"', err=True)
        raise typer.Exit(1)
    s.raw_dir.mkdir(parents=True, exist_ok=True)
    comp = s.raw["kaggle"]["competition"]
    subprocess.run([kaggle, "competitions", "download", "-c", comp, "-p", str(s.raw_dir)], check=True)
    for z in s.raw_dir.glob("*.zip"):
        with zipfile.ZipFile(z) as zf:
            zf.extractall(s.raw_dir)
        z.unlink()
    typer.echo(f"Files in {s.raw_dir}:")
    for p in sorted(s.raw_dir.glob("*.csv")):
        typer.echo(f"  {p.name:40s} {p.stat().st_size / 1e6:8.1f} MB")


@app.command()
def fixture(
    n: int = typer.Option(300, help="Number of synthetic applicants"),
    out: Path = typer.Option(None, help="Output folder (default data/fixture)"),
) -> None:
    """Generate a small synthetic dataset with the real Kaggle file/column names."""
    from hcdw.fixture import make_fixture

    out = out or get_settings().fixture_dir
    counts = make_fixture(out, n_customers=n)
    typer.echo(json.dumps(counts, indent=2))
    typer.echo(f"Written to {out}")


@app.command()
def sample(
    n: int = typer.Option(None, help="Number of applicants (default from settings.yaml)"),
    compress: bool = typer.Option(True, help="Write .csv.gz instead of .csv"),
) -> None:
    """Build data/sample/ from data/raw/ (stratified by TARGET, children filtered to match)."""
    from hcdw.sample import build_sample

    s = get_settings()
    cfg = s.raw["sample"]
    counts = build_sample(s.raw_dir, s.sample_dir, n or int(cfg["n_customers"]),
                          float(cfg["test_share"]), int(cfg["seed"]), compress=compress)
    typer.echo(json.dumps(counts, indent=2))


@app.command()
def etl(
    source: str = typer.Option("raw", help="raw | sample | fixture | <folder with the CSVs>"),
    push: bool = typer.Option(False, help="Upload to MotherDuck after a successful run"),
) -> None:
    """Run extract -> clean -> aggregate -> load -> quality into the local DuckDB file."""
    from hcdw.etl.pipeline import WarehouseLockedError, run

    try:
        report = run(_resolve_source(source))
    except (WarehouseLockedError, FileNotFoundError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    dq = report["data_quality"]
    typer.echo(json.dumps({"timings_sec": report["timings_sec"], "row_counts": dq["row_counts"]}, indent=2))
    for c in dq["checks"]:
        typer.echo(f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['name']}: {c['detail']}")
    if not dq["passed"]:
        typer.echo("Data quality checks failed.", err=True)
        raise typer.Exit(1)
    if push:
        _push()


@app.command()
def dq() -> None:
    """Re-run the data-quality checks on the current warehouse."""
    from hcdw.db import get_conn
    from hcdw.etl.quality import run_checks

    con = get_conn(read_only=get_settings().dw_target == "local")
    result = run_checks(con)
    con.close()
    for c in result["checks"]:
        typer.echo(f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['name']}: {c['detail']}")
    typer.echo(json.dumps(result["null_pct_fact_loan_application"], indent=2))
    if not result["passed"]:
        raise typer.Exit(1)


@app.command()
def olap(name: str = typer.Argument(None, help="File name (or prefix) in src/sql/olap; omit for all")) -> None:
    """Run the OLAP example queries (roll-up, cube, drill-down, slice/dice, pivot, ranking)."""
    from hcdw.db import get_conn

    files = sorted((SQL_DIR / "olap").glob("*.sql"))
    if name:
        files = [f for f in files if f.name.startswith(name)]
    con = get_conn(read_only=get_settings().dw_target == "local")
    for f in files:
        typer.echo(f"\n=== {f.name} ===")
        typer.echo(con.execute(f.read_text(encoding="utf-8")).df().to_string(index=False, max_rows=40))
    con.close()


def _push() -> None:
    from hcdw.db import push_to_motherduck

    db = push_to_motherduck()
    typer.echo(f"Uploaded to MotherDuck database '{db}'. Teammates: set DW_TARGET=motherduck.")


@app.command()
def push() -> None:
    """Upload data/warehouse/hc.duckdb to MotherDuck (replaces the shared database)."""
    _push()


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Interface to bind"),
    port: int = typer.Option(8000, help="Port"),
    reload: bool = typer.Option(False, help="Auto-reload on code changes (development)"),
) -> None:
    """Start the web app: JSON API under /api and the built React dashboard at /."""
    import uvicorn

    typer.echo(f"Dashboard: http://{host}:{port}   API docs: http://{host}:{port}/docs")
    uvicorn.run("hcdw.api.app:app", host=host, port=port, reload=reload)


@app.command()
def info() -> None:
    """Show which warehouse is configured and its table sizes."""
    from hcdw.db import get_conn

    s = get_settings()
    typer.echo(f"DW_TARGET = {s.dw_target}")
    typer.echo(f"local file = {s.dw_path}" if s.dw_target == "local" else f"MotherDuck db = {s.md_database}")
    con = get_conn(read_only=s.dw_target == "local")
    rows = con.execute("""
        SELECT schema_name, table_name, estimated_size
        FROM duckdb_tables() WHERE schema_name IN ('staging', 'dw')
        ORDER BY schema_name, table_name""").fetchall()
    for schema, table, size in rows:
        typer.echo(f"  {schema}.{table:28s} ~{size:>12,} rows")
    con.close()


if __name__ == "__main__":
    sys.exit(app())
