"""Multi-row merge logic on a hand-built staging area."""
import duckdb
import pytest

from hcdw.config import SQL_DIR
from hcdw.db import run_sql_file


@pytest.fixture
def staged():
    con = duckdb.connect()
    run_sql_file(con, SQL_DIR / "ddl" / "00_schemas.sql")
    run_sql_file(con, SQL_DIR / "ddl" / "01_staging.sql")
    con.execute("INSERT INTO staging.application (sk_id_curr, is_train) VALUES (1, true), (2, true), (3, false), (4, true)")
    # applicant 1: two bureau credits, one active and currently 5 days overdue; balance status up to 2 (31-60 DPD)
    con.execute("""INSERT INTO staging.bureau (sk_id_curr, sk_id_bureau, credit_active, credit_day_overdue,
                   amt_credit_sum_overdue, amt_credit_sum_debt, days_credit)
                   VALUES (1, 10, 'Active', 5, 100, 5000, -100), (1, 11, 'Closed', 0, 0, 0, -900)""")
    con.execute("""INSERT INTO staging.bureau_balance VALUES
                   (10, 0, '0'), (10, -1, '2'), (10, -2, 'X'), (11, 0, 'C'), (11, -1, '1')""")
    # applicant 2: no bureau, 3 previous apps (2 approved, 1 refused, 1 canceled), pays 100 days late once
    con.execute("""INSERT INTO staging.previous_application (sk_id_prev, sk_id_curr, name_contract_status)
                   VALUES (20, 2, 'Approved'), (21, 2, 'Approved'), (22, 2, 'Refused'), (23, 2, 'Canceled')""")
    con.execute("""INSERT INTO staging.installments_payments
                   (sk_id_prev, sk_id_curr, days_instalment, days_entry_payment, amt_instalment, amt_payment)
                   VALUES (20, 2, -500, -400, 100, 100), (20, 2, -470, -480, 100, 50)""")
    # applicant 4: a closed credit that still shows an overdue amount (stale bureau data)
    con.execute("""INSERT INTO staging.bureau (sk_id_curr, sk_id_bureau, credit_active, credit_day_overdue,
                   amt_credit_sum_overdue, days_credit) VALUES (4, 40, 'Closed', 0, 250, -700)""")
    run_sql_file(con, SQL_DIR / "transform" / "10_agg_credit_profile.sql")
    yield con
    con.close()


def profile(con, sk_id):
    cur = con.execute("SELECT * FROM staging.agg_credit_profile WHERE sk_id_curr = ?", [sk_id])
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, cur.fetchone()))


def test_one_profile_per_applicant(staged):
    assert staged.execute("SELECT COUNT(*), COUNT(DISTINCT sk_id_curr) FROM staging.agg_credit_profile").fetchone() == (4, 4)


def test_bureau_and_balance(staged):
    p = profile(staged, 1)
    assert p["cnt_bureau_active"] == 1
    assert p["bureau_active_bucket"] == "1-2"
    assert p["has_current_overdue"] is True
    assert p["max_dpd_days"] == 31  # bureau_balance status 2 -> 31+ days beats 5 days overdue
    assert p["max_dpd_bucket"] == "31-60"
    assert p["overdue_flag"] is True
    assert p["prev_approval_bucket"] == "No previous"


def test_previous_and_installments(staged):
    p = profile(staged, 2)
    assert p["bureau_active_bucket"] == "No bureau record"
    assert p["cnt_prev_applications"] == 4
    assert abs(p["prev_approval_rate"] - 2 / 3) < 1e-9   # canceled is ignored
    assert p["prev_approval_bucket"] == "50-99%"
    assert p["max_dpd_days"] == 100
    assert p["max_dpd_bucket"] == "90+"
    assert p["late_payment_ratio"] == 0.5


def test_applicant_without_history(staged):
    p = profile(staged, 3)
    assert p["max_dpd_days"] == 0
    assert p["max_dpd_bucket"] == "No DPD"
    assert p["overdue_flag"] is False


def test_overdue_on_closed_credit_is_not_current(staged):
    p = profile(staged, 4)
    assert p["has_current_overdue"] is False
    assert p["bureau_active_bucket"] == "0"
