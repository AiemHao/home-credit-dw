"""End-to-end ETL on the synthetic fixture + data-quality and constraint checks."""
import duckdb
import pytest

from hcdw.etl.pipeline import run
from hcdw.sample import build_sample
from tests.conftest import N_CUSTOMERS


def test_quality_checks_pass(built):
    _, report = built
    failed = [c for c in report["data_quality"]["checks"] if not c["passed"]]
    assert not failed, failed


def test_every_applicant_reaches_the_fact(dw):
    assert dw.execute("SELECT COUNT(*) FROM dw.fact_loan_application").fetchone()[0] == N_CUSTOMERS
    assert dw.execute("SELECT COUNT(*) FROM dw.dim_customer").fetchone()[0] == N_CUSTOMERS


def test_test_rows_have_no_target(dw):
    n = dw.execute("SELECT COUNT(*) FROM dw.fact_loan_application WHERE NOT is_train AND target IS NOT NULL").fetchone()[0]
    assert n == 0
    assert dw.execute("SELECT COUNT(*) FROM dw.fact_loan_application WHERE NOT is_train").fetchone()[0] > 0


def test_marts_are_queryable(dw):
    wide = dw.execute("SELECT COUNT(*) FROM mart.v_application_wide").fetchone()[0]
    assert wide == N_CUSTOMERS
    rate = dw.execute("SELECT default_rate FROM mart.kpi_portfolio_summary").fetchone()[0]
    assert 0 <= rate <= 1


def test_foreign_key_is_enforced(built, tmp_path):
    con = duckdb.connect(str(built[0]))  # writable copy is not needed: we roll back
    try:
        con.execute("BEGIN")
        with pytest.raises(duckdb.ConstraintException):
            con.execute("""INSERT INTO dw.fact_bureau_credit (bureau_credit_id, customer_key, bureau_category_key,
                           open_date_key) VALUES (-1, -999, 1, 20180517)""")
    finally:
        con.execute("ROLLBACK")
        con.close()


def test_rerun_is_idempotent(fixture_dir, tmp_path):
    dw_path = tmp_path / "rerun.duckdb"
    first = run(fixture_dir, dw_path=dw_path)["loaded_rows"]
    second = run(fixture_dir, dw_path=dw_path)["loaded_rows"]
    assert first == second


def test_sample_keeps_children_consistent(fixture_dir, tmp_path):
    out = tmp_path / "sample"
    counts = build_sample(fixture_dir, out, n_customers=60, test_share=0.2, seed=1, compress=True)
    assert counts["application_train"] + counts["application_test"] <= 60
    con = duckdb.connect()
    orphans = con.execute(f"""
        SELECT COUNT(*) FROM read_csv('{(out / 'bureau.csv.gz').as_posix()}') b
        WHERE b.SK_ID_CURR NOT IN (
            SELECT SK_ID_CURR FROM read_csv('{(out / 'application_train.csv.gz').as_posix()}')
            UNION ALL
            SELECT SK_ID_CURR FROM read_csv('{(out / 'application_test.csv.gz').as_posix()}'))""").fetchone()[0]
    assert orphans == 0
    report = run(out, dw_path=tmp_path / "sample.duckdb")
    assert report["data_quality"]["passed"]


def test_bureau_fact_uses_junk_dimension_and_close_dates(dw):
    n_cat, n_combos = dw.execute("""
        SELECT (SELECT COUNT(*) FROM dw.dim_bureau_category),
               (SELECT COUNT(*) FROM (SELECT DISTINCT credit_active, credit_type, credit_currency
                                      FROM mart.v_bureau_credit_wide))""").fetchone()
    assert n_cat >= n_combos > 0
    # only closed credits get a close date, never before the open date
    bad = dw.execute("""
        SELECT COUNT(*) FROM mart.v_bureau_credit_wide
        WHERE close_date IS NOT NULL AND (credit_active <> 'Closed' OR close_date < open_date
                                          OR credit_duration_days <> close_date - open_date)""").fetchone()[0]
    assert bad == 0
    # the fixture has one absurd DAYS_ENDDATE_FACT (-42000): it must be dropped, not crash the load
    closed, dated = dw.execute("""
        SELECT COUNT(*), COUNT(close_date_key) FROM mart.v_bureau_credit_wide
        WHERE credit_active = 'Closed'""").fetchone()
    assert dated == closed - 1


def test_failed_run_keeps_previous_warehouse(fixture_dir, tmp_path):
    dw_path = tmp_path / "keep.duckdb"
    run(fixture_dir, dw_path=dw_path)
    before = dw_path.stat().st_mtime_ns
    with pytest.raises(FileNotFoundError):
        run(tmp_path / "does-not-exist", dw_path=dw_path)
    assert dw_path.stat().st_mtime_ns == before
    assert not (tmp_path / "keep.duckdb.building").exists()
    con = duckdb.connect(str(dw_path), read_only=True)
    try:
        assert con.execute("SELECT COUNT(*) FROM dw.fact_loan_application").fetchone()[0] == N_CUSTOMERS
    finally:
        con.close()
