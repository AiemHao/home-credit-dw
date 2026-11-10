"""Synthetic mini-dataset with the real Kaggle file names and column names.

Used by the tests and by `hcdw fixture` so the pipeline and dashboard can be exercised before the
real 2.5 GB download. Values are random (seeded); only the shape matches the real data.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SENTINEL = 365243


def _choice(rng, values, n, p=None):
    return rng.choice(np.array(values, dtype=object), size=n, p=p)


def _with_nans(rng, arr, share):
    arr = np.asarray(arr, dtype=object)
    arr[rng.random(len(arr)) < share] = None
    return arr


def make_fixture(out_dir: Path, n_customers: int = 300, test_share: float = 0.2, seed: int = 7) -> dict[str, int]:
    rng = np.random.default_rng(seed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    n = n_customers
    ids = np.arange(100001, 100001 + n)
    is_test = rng.random(n) < test_share

    income_type = _choice(rng, ["Working", "Commercial associate", "Pensioner", "State servant"], n,
                          [0.5, 0.25, 0.17, 0.08])
    pensioner = income_type == "Pensioner"
    age_days = rng.integers(21 * 365, 69 * 365, n)
    income = np.round(rng.lognormal(np.log(150000), 0.5, n), -2)
    income[0] = 9_000_000  # one extreme outlier, like the real data
    credit = np.round(income * rng.uniform(1.5, 6, n), -2)
    goods = np.round(credit * rng.uniform(0.8, 1.0, n), -2)
    annuity = np.round(credit / rng.integers(12, 60, n), 1)
    ext = np.clip(rng.normal(0.5, 0.2, (n, 3)), 0.001, 0.999)
    ext[rng.random((n, 3)) < 0.2] = np.nan
    risk = 1 / (1 + np.exp(-(-2.4 - 3.0 * (np.nanmean(np.where(np.isnan(ext), 0.5, ext), axis=1) - 0.5))))
    target = (rng.random(n) < risk).astype(int)

    app = pd.DataFrame({
        "SK_ID_CURR": ids,
        "TARGET": target,
        "NAME_CONTRACT_TYPE": _choice(rng, ["Cash loans", "Revolving loans"], n, [0.9, 0.1]),
        "CODE_GENDER": _choice(rng, ["F", "M", "XNA"], n, [0.64, 0.35, 0.01]),
        "FLAG_OWN_CAR": _choice(rng, ["Y", "N"], n),
        "FLAG_OWN_REALTY": _choice(rng, ["Y", "N"], n),
        "CNT_CHILDREN": rng.poisson(0.4, n),
        "AMT_INCOME_TOTAL": income,
        "AMT_CREDIT": credit,
        "AMT_ANNUITY": annuity,
        "AMT_GOODS_PRICE": goods,
        "NAME_TYPE_SUITE": _with_nans(rng, _choice(rng, ["Unaccompanied", "Family", "Spouse, partner"], n), 0.05),
        "NAME_INCOME_TYPE": income_type,
        "NAME_EDUCATION_TYPE": _choice(rng, ["Secondary / secondary special", "Higher education",
                                             "Incomplete higher", "Lower secondary"], n, [0.7, 0.24, 0.04, 0.02]),
        "NAME_FAMILY_STATUS": _choice(rng, ["Married", "Single / not married", "Civil marriage",
                                            "Separated", "Widow", "Unknown"], n, [0.6, 0.15, 0.1, 0.07, 0.07, 0.01]),
        "NAME_HOUSING_TYPE": _choice(rng, ["House / apartment", "With parents", "Municipal apartment",
                                           "Rented apartment"], n, [0.88, 0.05, 0.04, 0.03]),
        "REGION_POPULATION_RELATIVE": np.round(rng.uniform(0.0005, 0.072, n), 6),
        "DAYS_BIRTH": -age_days,
        "DAYS_EMPLOYED": np.where(pensioner, SENTINEL, -rng.integers(0, 40 * 365, n)),
        "DAYS_REGISTRATION": -rng.integers(0, 20000, n).astype(float),
        "DAYS_ID_PUBLISH": -rng.integers(0, 7000, n),
        "OWN_CAR_AGE": _with_nans(rng, rng.integers(0, 30, n), 0.6),
        "FLAG_MOBIL": 1,  # extra column the warehouse ignores
        "OCCUPATION_TYPE": _with_nans(rng, _choice(rng, ["Laborers", "Sales staff", "Core staff", "Managers",
                                                         "Drivers", "Accountants"], n), 0.3),
        "CNT_FAM_MEMBERS": rng.integers(1, 5, n).astype(float),
        "REGION_RATING_CLIENT": _choice(rng, [1, 2, 3], n, [0.1, 0.74, 0.16]),
        "REGION_RATING_CLIENT_W_CITY": _choice(rng, [1, 2, 3], n, [0.11, 0.75, 0.14]),
        "WEEKDAY_APPR_PROCESS_START": _choice(rng, ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY",
                                                    "SATURDAY", "SUNDAY"], n),
        "HOUR_APPR_PROCESS_START": rng.integers(0, 24, n),
        "REG_REGION_NOT_LIVE_REGION": rng.integers(0, 2, n),
        "REG_REGION_NOT_WORK_REGION": rng.integers(0, 2, n),
        "LIVE_REGION_NOT_WORK_REGION": rng.integers(0, 2, n),
        "REG_CITY_NOT_LIVE_CITY": rng.integers(0, 2, n),
        "REG_CITY_NOT_WORK_CITY": rng.integers(0, 2, n),
        "LIVE_CITY_NOT_WORK_CITY": rng.integers(0, 2, n),
        "ORGANIZATION_TYPE": np.where(pensioner, "XNA",
                                      _choice(rng, ["Business Entity Type 3", "Self-employed", "Government"], n)),
        "EXT_SOURCE_1": ext[:, 0],
        "EXT_SOURCE_2": ext[:, 1],
        "EXT_SOURCE_3": ext[:, 2],
        "DAYS_LAST_PHONE_CHANGE": -rng.integers(0, 4000, n).astype(float),
        "AMT_REQ_CREDIT_BUREAU_YEAR": rng.integers(0, 5, n).astype(float),
    })
    # application_test really contains one REGION_RATING_CLIENT_W_CITY = -1; keep that edge case.
    if is_test.any():
        app.loc[np.flatnonzero(is_test)[0], "REGION_RATING_CLIENT_W_CITY"] = -1
    train = app[~is_test].copy()
    test = app[is_test].drop(columns=["TARGET"]).copy()

    # bureau: 0-6 credits per applicant
    n_bureau = rng.integers(0, 7, n)
    b_curr = np.repeat(ids, n_bureau)
    nb = len(b_curr)
    b_active = _choice(rng, ["Closed", "Active", "Sold", "Bad debt"], nb, [0.62, 0.36, 0.015, 0.005])
    overdue_days = np.where(rng.random(nb) < 0.03, rng.integers(1, 120, nb), 0)
    days_credit = -rng.integers(1, 2900, nb)
    # Only closed credits have an actual end date, a few weeks to a few years after opening.
    end_fact = np.where(b_active == "Closed",
                        np.minimum(days_credit + rng.integers(30, 1500, nb), 0), np.nan).astype(float)
    closed_idx = np.flatnonzero(b_active == "Closed")
    if len(closed_idx):
        end_fact[closed_idx[0]] = -42000.0  # absurd value like the real file: must not break dim_time
    bureau = pd.DataFrame({
        "SK_ID_CURR": b_curr,
        "SK_ID_BUREAU": np.arange(5000001, 5000001 + nb),
        "CREDIT_ACTIVE": b_active,
        "CREDIT_CURRENCY": _choice(rng, ["currency 1", "currency 2"], nb, [0.99, 0.01]),
        "DAYS_CREDIT": days_credit,
        "CREDIT_DAY_OVERDUE": overdue_days,
        "DAYS_CREDIT_ENDDATE": rng.integers(-2000, 2000, nb).astype(float),
        "DAYS_ENDDATE_FACT": end_fact,
        "AMT_CREDIT_MAX_OVERDUE": _with_nans(rng, rng.uniform(0, 5000, nb).round(2), 0.6),
        "CNT_CREDIT_PROLONG": rng.integers(0, 2, nb),
        "AMT_CREDIT_SUM": np.round(rng.lognormal(np.log(200000), 0.8, nb), 2),
        "AMT_CREDIT_SUM_DEBT": np.where(b_active == "Active", np.round(rng.uniform(0, 150000, nb), 2), 0.0),
        "AMT_CREDIT_SUM_LIMIT": _with_nans(rng, np.zeros(nb), 0.3),
        "AMT_CREDIT_SUM_OVERDUE": np.where(overdue_days > 0, np.round(rng.uniform(100, 5000, nb), 2), 0.0),
        "CREDIT_TYPE": _choice(rng, ["Consumer credit", "Credit card", "Car loan", "Mortgage"], nb,
                               [0.73, 0.23, 0.02, 0.02]),
        "DAYS_CREDIT_UPDATE": -rng.integers(0, 1000, nb),
        "AMT_ANNUITY": _with_nans(rng, rng.uniform(0, 20000, nb).round(2), 0.7),
    })

    # bureau_balance: 0-12 months per bureau credit
    n_months = rng.integers(0, 13, nb)
    bb_id = np.repeat(bureau["SK_ID_BUREAU"].to_numpy(), n_months)
    bb_month = -np.concatenate([np.arange(k) for k in n_months]) if nb else np.array([], dtype=int)
    bureau_balance = pd.DataFrame({
        "SK_ID_BUREAU": bb_id,
        "MONTHS_BALANCE": bb_month,
        "STATUS": _choice(rng, ["C", "X", "0", "1", "2", "3", "5"], len(bb_id),
                          [0.4, 0.2, 0.33, 0.04, 0.015, 0.01, 0.005]),
    })

    # previous applications: 0-4 per applicant
    n_prev = rng.integers(0, 5, n)
    p_curr = np.repeat(ids, n_prev)
    npv = len(p_curr)
    prev = pd.DataFrame({
        "SK_ID_PREV": np.arange(2000001, 2000001 + npv),
        "SK_ID_CURR": p_curr,
        "NAME_CONTRACT_TYPE": _choice(rng, ["Consumer loans", "Cash loans", "Revolving loans"], npv),
        "AMT_ANNUITY": rng.uniform(1000, 30000, npv).round(2),
        "AMT_APPLICATION": rng.uniform(10000, 500000, npv).round(2),
        "AMT_CREDIT": rng.uniform(10000, 500000, npv).round(2),
        "AMT_GOODS_PRICE": rng.uniform(10000, 500000, npv).round(2),
        "NAME_CONTRACT_STATUS": _choice(rng, ["Approved", "Refused", "Canceled", "Unused offer"], npv,
                                        [0.62, 0.17, 0.19, 0.02]),
        "DAYS_DECISION": -rng.integers(1, 2900, npv),
        "NAME_CLIENT_TYPE": _choice(rng, ["Repeater", "New", "Refreshed"], npv),
        "NAME_PORTFOLIO": _choice(rng, ["POS", "Cash", "XNA", "Cards"], npv),
        "NAME_YIELD_GROUP": _choice(rng, ["middle", "high", "low_normal", "XNA"], npv),
        "CNT_PAYMENT": rng.integers(6, 48, npv).astype(float),
    })

    # installments / POS / credit card: per previous application
    n_inst = rng.integers(1, 11, npv)
    i_prev = np.repeat(prev["SK_ID_PREV"].to_numpy(), n_inst)
    i_curr = np.repeat(prev["SK_ID_CURR"].to_numpy(), n_inst)
    ni = len(i_prev)
    due = -rng.integers(1, 2900, ni).astype(float)
    paid_delay = np.where(rng.random(ni) < 0.1, rng.integers(1, 100, ni), -rng.integers(0, 15, ni))
    amt_inst = rng.uniform(1000, 30000, ni).round(2)
    installments = pd.DataFrame({
        "SK_ID_PREV": i_prev,
        "SK_ID_CURR": i_curr,
        "NUM_INSTALMENT_VERSION": 1.0,
        "NUM_INSTALMENT_NUMBER": np.concatenate([np.arange(1, k + 1) for k in n_inst]) if npv else [],
        "DAYS_INSTALMENT": due,
        "DAYS_ENTRY_PAYMENT": due + paid_delay,
        "AMT_INSTALMENT": amt_inst,
        "AMT_PAYMENT": np.where(rng.random(ni) < 0.05, amt_inst * 0.5, amt_inst).round(2),
    })

    pos = pd.DataFrame({
        "SK_ID_PREV": i_prev,
        "SK_ID_CURR": i_curr,
        "MONTHS_BALANCE": -rng.integers(1, 96, ni),
        "CNT_INSTALMENT": rng.integers(6, 48, ni).astype(float),
        "CNT_INSTALMENT_FUTURE": rng.integers(0, 48, ni).astype(float),
        "NAME_CONTRACT_STATUS": _choice(rng, ["Active", "Completed"], ni, [0.9, 0.1]),
        "SK_DPD": np.where(rng.random(ni) < 0.03, rng.integers(1, 200, ni), 0),
        "SK_DPD_DEF": 0,
    })

    cc_mask = prev["NAME_CONTRACT_TYPE"].to_numpy() == "Revolving loans"
    cc_prev = prev[cc_mask]
    n_cc = rng.integers(1, 6, len(cc_prev))
    nc = int(n_cc.sum())
    limit = rng.choice([0, 45000, 90000, 135000], nc).astype(float)
    credit_card = pd.DataFrame({
        "SK_ID_PREV": np.repeat(cc_prev["SK_ID_PREV"].to_numpy(), n_cc),
        "SK_ID_CURR": np.repeat(cc_prev["SK_ID_CURR"].to_numpy(), n_cc),
        "MONTHS_BALANCE": -rng.integers(1, 96, nc),
        "AMT_BALANCE": (limit * rng.uniform(0, 1, nc)).round(2),
        "AMT_CREDIT_LIMIT_ACTUAL": limit,
        "AMT_DRAWINGS_CURRENT": rng.uniform(0, 10000, nc).round(2),
        "AMT_PAYMENT_TOTAL_CURRENT": rng.uniform(0, 10000, nc).round(2),
        "AMT_INST_MIN_REGULARITY": rng.uniform(0, 5000, nc).round(2),
        "SK_DPD": np.where(rng.random(nc) < 0.03, rng.integers(1, 60, nc), 0),
        "SK_DPD_DEF": 0,
    })

    files = {
        "application_train": train,
        "application_test": test,
        "bureau": bureau,
        "bureau_balance": bureau_balance,
        "previous_application": prev,
        "installments_payments": installments,
        "POS_CASH_balance": pos,
        "credit_card_balance": credit_card,
    }
    for stem, df in files.items():
        df.to_csv(out_dir / f"{stem}.csv", index=False)
    return {stem: len(df) for stem, df in files.items()}
