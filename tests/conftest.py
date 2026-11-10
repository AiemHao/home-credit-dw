from __future__ import annotations

import duckdb
import pytest

from hcdw.etl.pipeline import run
from hcdw.fixture import make_fixture

N_CUSTOMERS = 250


@pytest.fixture(scope="session")
def fixture_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("fixture")
    make_fixture(d, n_customers=N_CUSTOMERS, seed=11)
    return d


@pytest.fixture(scope="session")
def built(fixture_dir, tmp_path_factory):
    """Run the full pipeline once on the synthetic data; returns (dw_path, report)."""
    dw_path = tmp_path_factory.mktemp("dw") / "test.duckdb"
    report = run(fixture_dir, dw_path=dw_path)
    return dw_path, report


@pytest.fixture
def dw(built):
    con = duckdb.connect(str(built[0]), read_only=True)
    yield con
    con.close()
