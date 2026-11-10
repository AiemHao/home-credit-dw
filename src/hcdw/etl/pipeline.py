"""End-to-end ETL: extract -> clean -> aggregate -> load -> quality. Always builds the LOCAL file;
use `hcdw push` (or `hcdw etl --push`) to publish it to MotherDuck.

The warehouse is built in a side file (<dw>.building) and swapped in only after every step has
succeeded, so a failed or interrupted run never leaves a half-built warehouse behind.
"""
from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from hcdw.config import get_settings
from hcdw.db import get_conn
from hcdw.etl.aggregate import aggregate
from hcdw.etl.clean import clean
from hcdw.etl.extract import extract
from hcdw.etl.load import load
from hcdw.etl.quality import run_checks

log = logging.getLogger(__name__)


class WarehouseLockedError(RuntimeError):
    """The finished warehouse could not replace the old file (another process has it open)."""


def _remove(*paths: Path) -> None:
    for p in paths:
        p.unlink(missing_ok=True)


@contextmanager
def _step(name: str, timings: dict[str, float]):
    log.info("== %s ...", name)
    t0 = time.perf_counter()
    yield
    timings[name] = round(time.perf_counter() - t0, 2)
    log.info("== %s done in %.2fs", name, timings[name])


def run(source_dir: Path, dw_path: Path | None = None) -> dict:
    settings = get_settings()
    dw_path = Path(dw_path or settings.dw_path)
    building = dw_path.with_name(dw_path.name + ".building")
    _remove(building, Path(f"{building}.wal"))
    timings: dict[str, float] = {}
    con = get_conn("local", path=building)
    # Row order of staging tables does not matter; dropping the guarantee saves memory on 27M-row files.
    con.execute("SET preserve_insertion_order = false")
    try:
        with _step("extract", timings):
            extracted = extract(con, source_dir)
        with _step("clean", timings):
            cleaned = clean(con, settings)
        with _step("aggregate", timings):
            aggregated = aggregate(con)
        with _step("load", timings):
            loaded = load(con, settings)
        with _step("quality", timings):
            dq = run_checks(con)
        con.execute("CHECKPOINT")
    except BaseException:
        con.close()
        _remove(building, Path(f"{building}.wal"))
        raise
    con.close()

    try:
        _remove(Path(f"{dw_path}.wal"))  # a stale WAL must never be replayed onto the new file
        os.replace(building, dw_path)
    except PermissionError as exc:
        raise WarehouseLockedError(
            f"{dw_path.name} is open in another process (dashboard?). Close it and run the ETL again; "
            f"the old warehouse is unchanged."
        ) from exc

    report = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "source_dir": str(source_dir),
        "dw_path": str(dw_path),
        "timings_sec": timings,
        "extracted_rows": extracted,
        "cleaned_applications": cleaned,
        "aggregated_rows": aggregated,
        "loaded_rows": loaded,
        "data_quality": dq,
    }
    report_path = dw_path.parent / settings.dq_report.name
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log.info("report written to %s", report_path)
    return report
