"""Clean: staging.application -> staging.application_clean (pandas).

Rules (document each one in docs/etl_mapping.md):
  R1  DAYS_EMPLOYED = 365243 is a sentinel (mostly pensioners) -> NULL + is_employed_anomaly flag
  R2  'XNA' / 'Unknown' / empty categorical values -> 'Unknown'
  R3  CODE_GENDER outside {M, F} -> 'Unknown'
  R4  income above the configured quantile -> is_income_outlier flag; ratios use the capped income
  R5  age_years = -DAYS_BIRTH / 365.25, years_employed = -DAYS_EMPLOYED / 365.25
  R6  age_bucket / income_bracket from configs/settings.yaml
  R7  ratios: debt_to_income = annuity / income, credit_to_income, credit_to_goods
  R8  ext_source_mean = mean of available EXT_SOURCE_1..3
  R9  derived bands: appr_hour_band, population_density_band; 0/1 flags -> booleans
  R10 region ratings outside 1..3 -> NULL (application_test has a -1)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from hcdw.config import Settings

UNKNOWN = "Unknown"
MISSING_TOKENS = {"XNA", "XAP", "Unknown", ""}


def _category(s: pd.Series) -> pd.Series:
    s = s.astype("object").where(~s.isin(MISSING_TOKENS), None)
    return s.fillna(UNKNOWN).astype(str)


def _bucket(values: pd.Series, edges: list[float], labels: list[str]) -> pd.Series:
    cut = pd.cut(values, bins=edges, labels=labels, right=False)
    return cut.astype("object").where(cut.notna(), UNKNOWN).astype(str)


def _flag(s: pd.Series) -> pd.Series:
    return s.map({1: True, 0: False}).astype("boolean")


def _yn(s: pd.Series) -> pd.Series:
    return s.map({"Y": True, "N": False}).astype("boolean")


def _rating(s: pd.Series) -> pd.Series:
    """Region ratings are 1..3; anything else (e.g. -1 in application_test) becomes NULL."""
    s = s.astype("Int64")
    return s.where(s.between(1, 3))


def clean_application(df: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    cfg = settings.raw["cleaning"]
    sentinel = int(cfg["days_employed_sentinel"])
    out = pd.DataFrame(index=df.index)

    out["sk_id_curr"] = df["sk_id_curr"].astype("int64")
    out["target"] = df["target"].astype("Int64")
    out["is_train"] = df["is_train"].astype(bool)

    # Customer attributes
    gender = df["code_gender"].astype("object")
    out["gender"] = gender.where(gender.isin(["M", "F"]), UNKNOWN)
    out["own_car"] = _yn(df["flag_own_car"])
    out["own_realty"] = _yn(df["flag_own_realty"])
    out["cnt_children"] = df["cnt_children"].astype("Int64")
    out["cnt_fam_members"] = df["cnt_fam_members"]
    for src, dst in [
        ("name_income_type", "income_type"),
        ("name_education_type", "education_type"),
        ("name_family_status", "family_status"),
        ("name_housing_type", "housing_type"),
        ("occupation_type", "occupation_type"),
        ("organization_type", "organization_type"),
        ("name_contract_type", "contract_type"),
        ("name_type_suite", "accompanied_by"),
        ("weekday_appr_process_start", "appr_weekday"),
    ]:
        out[dst] = _category(df[src])

    # R1 + R5: ages and employment length
    days_emp = df["days_employed"]
    out["is_employed_anomaly"] = (days_emp == sentinel).fillna(False).astype(bool)
    days_emp = days_emp.where(days_emp != sentinel)
    out["years_employed"] = (-days_emp / 365.25).clip(lower=0)
    out["age_years"] = -df["days_birth"] / 365.25

    # R4: income outliers
    income = df["amt_income_total"].astype(float)
    cap = float(income.quantile(float(cfg["income_outlier_quantile"])))
    out["amt_income_total"] = income
    out["is_income_outlier"] = (income > cap).fillna(False).astype(bool)
    income_capped = income.clip(upper=cap)

    # R6: buckets
    out["age_bucket"] = _bucket(out["age_years"], *settings.bucket("age_years"))
    out["income_bracket"] = _bucket(income, *settings.bucket("income"))

    # Amounts + R7 ratios
    out["amt_credit"] = df["amt_credit"]
    out["amt_annuity"] = df["amt_annuity"]
    out["amt_goods_price"] = df["amt_goods_price"]
    out["debt_to_income"] = df["amt_annuity"] / income_capped
    out["credit_to_income"] = df["amt_credit"] / income_capped
    out["credit_to_goods"] = df["amt_credit"] / df["amt_goods_price"].replace(0, np.nan)

    # R8
    for c in ("ext_source_1", "ext_source_2", "ext_source_3"):
        out[c] = df[c]
    out["ext_source_mean"] = df[["ext_source_1", "ext_source_2", "ext_source_3"]].mean(axis=1, skipna=True)

    # R9: region + application timing
    out["region_rating_client"] = _rating(df["region_rating_client"])
    out["region_rating_city"] = _rating(df["region_rating_client_w_city"])
    out["population_density_band"] = _bucket(
        df["region_population_relative"], [0, 0.01, 0.03, np.inf], ["Low", "Medium", "High"]
    )
    out["reg_city_not_live_city"] = _flag(df["reg_city_not_live_city"])
    out["reg_city_not_work_city"] = _flag(df["reg_city_not_work_city"])
    out["reg_region_not_live_region"] = _flag(df["reg_region_not_live_region"])
    out["appr_hour_band"] = _bucket(
        df["hour_appr_process_start"], [0, 6, 12, 18, 24], ["Night", "Morning", "Afternoon", "Evening"]
    )
    return out.reset_index(drop=True)


def clean(con, settings: Settings) -> int:
    df = con.execute("SELECT * FROM staging.application").df()
    out = clean_application(df, settings)
    con.register("_application_clean_df", out)
    try:
        con.execute("CREATE OR REPLACE TABLE staging.application_clean AS SELECT * FROM _application_clean_df")
    finally:
        con.unregister("_application_clean_df")
    return len(out)
