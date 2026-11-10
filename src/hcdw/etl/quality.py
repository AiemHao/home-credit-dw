"""Data-quality checks on the loaded warehouse. Results go to data/warehouse/dq_report.json."""
from __future__ import annotations

from dataclasses import asdict, dataclass

PRIMARY_KEYS = {
    "dim_time": "date_key",
    "dim_customer": "customer_key",
    "dim_credit_history": "credit_history_key",
    "dim_contract": "contract_key",
    "dim_region": "region_key",
    "dim_bureau_category": "bureau_category_key",
    "fact_loan_application": "application_id",
    "fact_bureau_credit": "bureau_credit_id",
}

FOREIGN_KEYS = [
    ("fact_loan_application", "customer_key", "dim_customer", "customer_key"),
    ("fact_loan_application", "credit_history_key", "dim_credit_history", "credit_history_key"),
    ("fact_loan_application", "contract_key", "dim_contract", "contract_key"),
    ("fact_loan_application", "region_key", "dim_region", "region_key"),
    ("fact_loan_application", "application_date_key", "dim_time", "date_key"),
    ("fact_bureau_credit", "customer_key", "dim_customer", "customer_key"),
    ("fact_bureau_credit", "bureau_category_key", "dim_bureau_category", "bureau_category_key"),
    ("fact_bureau_credit", "open_date_key", "dim_time", "date_key"),
    ("fact_bureau_credit", "close_date_key", "dim_time", "date_key"),  # nullable: NULLs are not orphans
]

NULL_PROFILE_COLUMNS = [
    "target", "amt_annuity", "amt_goods_price", "debt_to_income",
    "ext_source_mean", "prev_approval_rate", "late_payment_ratio",
]


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


def _one(con, sql: str):
    return con.execute(sql).fetchone()[0]


def _close(a: float, b: float, rel: float = 1e-9) -> bool:
    return abs(a - b) <= rel * max(abs(a), abs(b), 1.0)


def run_checks(con) -> dict:
    checks: list[Check] = []

    for table, pk in PRIMARY_KEYS.items():
        dupes = _one(con, f"SELECT COUNT(*) - COUNT(DISTINCT {pk}) FROM dw.{table}")
        nulls = _one(con, f"SELECT COUNT(*) FROM dw.{table} WHERE {pk} IS NULL")
        checks.append(Check(f"pk_unique:{table}", dupes == 0 and nulls == 0,
                            f"{dupes} duplicate, {nulls} null keys"))

    for fact, col, dim, dim_col in FOREIGN_KEYS:
        orphans = _one(con, f"""
            SELECT COUNT(*) FROM dw.{fact} f
            WHERE f.{col} IS NOT NULL AND NOT EXISTS (SELECT 1 FROM dw.{dim} d WHERE d.{dim_col} = f.{col})""")
        checks.append(Check(f"fk:{fact}.{col}->{dim}", orphans == 0, f"{orphans} orphan rows"))

    staged = _one(con, "SELECT COUNT(*) FROM staging.application")
    loaded = _one(con, "SELECT COUNT(*) FROM dw.fact_loan_application")
    checks.append(Check("completeness:applications", staged == loaded,
                        f"staging {staged} vs fact {loaded}"))

    bad_target = _one(con, "SELECT COUNT(*) FROM dw.fact_loan_application WHERE NOT is_train AND target IS NOT NULL")
    checks.append(Check("target_only_on_train", bad_target == 0, f"{bad_target} test rows with TARGET"))

    # Reconciliation: the money that went in is the money that came out.
    src_credit = _one(con, "SELECT COALESCE(SUM(amt_credit), 0) FROM staging.application")
    dw_credit = _one(con, "SELECT COALESCE(SUM(amt_credit), 0) FROM dw.fact_loan_application")
    checks.append(Check("reconcile:sum_amt_credit", _close(src_credit, dw_credit),
                        f"staging {src_credit:,.0f} vs fact {dw_credit:,.0f}"))

    # Bureau rows can only be loaded for applicants we know and with an open date.
    expected_b = _one(con, """
        SELECT COUNT(*) FROM staging.bureau b
        WHERE b.sk_id_bureau IS NOT NULL AND b.days_credit IS NOT NULL
          AND b.sk_id_curr IN (SELECT sk_id_curr FROM staging.application)""")
    loaded_b = _one(con, "SELECT COUNT(*) FROM dw.fact_bureau_credit")
    checks.append(Check("completeness:bureau_credits", expected_b == loaded_b,
                        f"loadable staging {expected_b} vs fact {loaded_b}"))
    src_b = _one(con, """
        SELECT COALESCE(SUM(amt_credit_sum), 0) FROM staging.bureau
        WHERE sk_id_bureau IS NOT NULL AND days_credit IS NOT NULL
          AND sk_id_curr IN (SELECT sk_id_curr FROM staging.application)""")
    dw_b = _one(con, "SELECT COALESCE(SUM(amt_credit_sum), 0) FROM dw.fact_bureau_credit")
    checks.append(Check("reconcile:sum_bureau_credit", _close(src_b, dw_b),
                        f"staging {src_b:,.0f} vs fact {dw_b:,.0f}"))

    # Informational (always pass): what share of the source survives, and data-shape facts for the report.
    staged_b = _one(con, "SELECT COUNT(*) FROM staging.bureau")
    coverage = loaded_b / staged_b if staged_b else 1.0
    checks.append(Check("info:bureau_coverage", True,
                        f"{loaded_b}/{staged_b} bureau rows ({coverage:.1%}); the rest belong to unknown applicants"))
    closed, dated = con.execute("""
        SELECT COUNT(*) FILTER (WHERE g.credit_active = 'Closed'),
               COUNT(*) FILTER (WHERE g.credit_active = 'Closed' AND f.close_date_key IS NOT NULL)
        FROM dw.fact_bureau_credit f JOIN dw.dim_bureau_category g USING (bureau_category_key)""").fetchone()
    checks.append(Check("info:close_date_coverage", True, f"{dated}/{closed} closed credits have a usable close date"))
    rate = _one(con, "SELECT AVG(target) FROM dw.fact_loan_application WHERE is_train")
    checks.append(Check("info:train_default_rate", True,
                        "no labelled rows" if rate is None else f"{rate:.2%} of labelled applications defaulted"))

    total = max(loaded, 1)
    null_pct = {
        c: round(_one(con, f"SELECT COUNT(*) FROM dw.fact_loan_application WHERE {c} IS NULL") / total * 100, 2)
        for c in NULL_PROFILE_COLUMNS
    }
    row_counts = {t: _one(con, f"SELECT COUNT(*) FROM dw.{t}") for t in PRIMARY_KEYS}

    return {
        "passed": all(c.passed for c in checks),
        "checks": [asdict(c) for c in checks],
        "row_counts": row_counts,
        "null_pct_fact_loan_application": null_pct,
    }
