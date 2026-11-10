import numpy as np
import pandas as pd

from hcdw.config import get_settings
from hcdw.etl.clean import clean_application


def _row(**overrides):
    base = dict(
        sk_id_curr=1, target=0, is_train=True, name_contract_type="Cash loans", code_gender="F",
        flag_own_car="Y", flag_own_realty="N", cnt_children=0, amt_income_total=150000.0,
        amt_credit=600000.0, amt_annuity=30000.0, amt_goods_price=500000.0, name_type_suite=None,
        name_income_type="Working", name_education_type="Higher education", name_family_status="Married",
        name_housing_type="House / apartment", region_population_relative=0.02, days_birth=-int(30 * 365.25),
        days_employed=-3650, occupation_type=None, cnt_fam_members=2.0, region_rating_client=2,
        region_rating_client_w_city=2, weekday_appr_process_start="MONDAY", hour_appr_process_start=10,
        reg_region_not_live_region=0, reg_city_not_live_city=1, reg_city_not_work_city=0,
        organization_type="XNA", ext_source_1=np.nan, ext_source_2=0.4, ext_source_3=0.6,
    )
    base.update(overrides)
    return base


def test_cleaning_rules():
    df = pd.DataFrame([
        _row(sk_id_curr=1),
        _row(sk_id_curr=2, days_employed=365243, code_gender="XNA", name_income_type="Pensioner",
             days_birth=-int(66 * 365.25), amt_income_total=90000.0, hour_appr_process_start=3),
    ])
    out = clean_application(df, get_settings()).set_index("sk_id_curr")

    # R1 sentinel
    assert not out.loc[1, "is_employed_anomaly"] and out.loc[2, "is_employed_anomaly"]
    assert pd.isna(out.loc[2, "years_employed"])
    assert abs(out.loc[1, "years_employed"] - 3650 / 365.25) < 1e-9
    # R2 / R3 unknowns
    assert out.loc[1, "occupation_type"] == "Unknown"
    assert out.loc[1, "organization_type"] == "Unknown"
    assert out.loc[1, "accompanied_by"] == "Unknown"
    assert out.loc[2, "gender"] == "Unknown"
    # R6 buckets
    assert out.loc[1, "age_bucket"] == "25-34"
    assert out.loc[2, "age_bucket"] == "65+"
    assert out.loc[1, "income_bracket"] == "150k-200k"
    assert out.loc[2, "income_bracket"] == "<100k"
    # R7 / R8 ratios
    assert abs(out.loc[1, "credit_to_goods"] - 1.2) < 1e-9
    assert abs(out.loc[1, "ext_source_mean"] - 0.5) < 1e-9
    # R9 bands and flags
    assert out.loc[1, "appr_hour_band"] == "Morning"
    assert out.loc[2, "appr_hour_band"] == "Night"
    assert out.loc[1, "population_density_band"] == "Medium"
    assert bool(out.loc[1, "reg_city_not_live_city"]) is True
    assert bool(out.loc[1, "own_car"]) is True


def test_income_outlier_is_flagged_and_capped():
    rows = [_row(sk_id_curr=i, amt_income_total=100000.0) for i in range(1, 2000)]
    rows.append(_row(sk_id_curr=9999, amt_income_total=1.0e8))
    out = clean_application(pd.DataFrame(rows), get_settings()).set_index("sk_id_curr")
    assert out.loc[9999, "is_income_outlier"]
    assert out["is_income_outlier"].sum() == 1
    # the ratio uses the capped income, so it is not ~0
    assert out.loc[9999, "debt_to_income"] > 0.01


def test_region_rating_outside_domain_becomes_null():
    df = pd.DataFrame([_row(sk_id_curr=1), _row(sk_id_curr=2, region_rating_client_w_city=-1)])
    out = clean_application(df, get_settings()).set_index("sk_id_curr")
    assert out.loc[1, "region_rating_city"] == 2
    assert pd.isna(out.loc[2, "region_rating_city"])
