"""Feature matrix for the risk model.

Rule: read from the warehouse (mart.v_application_wide), never from the raw CSVs, so the model and
the dashboard see the same cleaned data. Need a raw column that is not in the warehouse yet? Add it
to src/sql/ddl/01_staging.sql + the transforms.
"""
from __future__ import annotations

import pandas as pd

NUMERIC_FEATURES = [
    "amt_income", "amt_credit", "amt_annuity", "amt_goods_price",
    "debt_to_income", "credit_to_income", "credit_to_goods", "ext_source_mean",
    "age_years", "years_employed", "cnt_children", "cnt_fam_members",
    "cnt_bureau_active", "cnt_prev_applications", "prev_approval_rate",
    "max_dpd_days", "late_payment_ratio", "region_rating_client",
]
CATEGORICAL_FEATURES = [
    "gender", "income_type", "education_type", "family_status", "housing_type",
    "occupation_type", "contract_type", "max_dpd_bucket", "bureau_active_bucket",
]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def load_frame(con, labelled: bool = True) -> pd.DataFrame:
    """labelled=True -> train rows with TARGET; False -> test rows to score."""
    cols = ", ".join(["application_id", "target", *FEATURES])
    df = con.execute(
        f"SELECT {cols} FROM mart.v_application_wide WHERE is_train = ?", [labelled]
    ).df()
    return prepare(df)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in CATEGORICAL_FEATURES:
        if c in df:
            df[c] = df[c].astype("category")
    return df
