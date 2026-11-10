"""Risk Simulator - DSS what-if page.

Skeleton: sliders -> feature row -> dss.predict.score -> dss.rules.evaluate.
TODO: choose the sliders that matter (from feature importance), add SHAP explanation,
and a batch tab that scores the test applications (is_train = false).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components.page import bootstrap
from dss.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES
from dss.predict import model_available, score
from dss.rules import GREEN, RED, evaluate
from queries import distinct_values

bootstrap("Risk Simulator", icon="🧮")

if not model_available():
    st.info("No trained model in models/model.pkl yet - decisions use business rules only. "
            "Train one with `python -m dss.train`.")

c1, c2, c3 = st.columns(3)
with c1:
    income = st.slider("Annual income", 25_000, 1_000_000, 180_000, step=5_000)
    credit = st.slider("Credit amount", 45_000, 4_000_000, 600_000, step=5_000)
    annuity = st.slider("Annuity", 2_000, 250_000, 27_000, step=500)
with c2:
    age = st.slider("Age (years)", 21, 69, 38)
    years_emp = st.slider("Years employed", 0, 45, 5)
    ext = st.slider("External score (mean EXT_SOURCE)", 0.0, 1.0, 0.5, step=0.01)
with c3:
    max_dpd = st.slider("Max days past due (history)", 0, 365, 0)
    bureau_active = st.slider("Active bureau credits", 0, 15, 1)
    overdue_now = st.checkbox("Currently overdue in bureau")
    income_type = st.selectbox("Employment type", distinct_values("income_type"))
    contract_type = st.selectbox("Contract type", distinct_values("contract_type"))

row = {c: None for c in NUMERIC_FEATURES + CATEGORICAL_FEATURES}
row.update({
    "amt_income": income, "amt_credit": credit, "amt_annuity": annuity, "amt_goods_price": credit * 0.9,
    "debt_to_income": annuity / income, "credit_to_income": credit / income, "credit_to_goods": 1 / 0.9,
    "ext_source_mean": ext, "age_years": age, "years_employed": years_emp,
    "cnt_bureau_active": bureau_active, "max_dpd_days": max_dpd,
    "income_type": income_type, "contract_type": contract_type,
})

p = None
if model_available():
    try:
        p = float(score(pd.DataFrame([row])).iloc[0])
    except Exception as exc:  # surface model/feature mismatches while the model evolves
        st.warning(f"Model scoring failed: {exc}")

decision = evaluate({**row, "has_current_overdue": overdue_now}, p)
color = {GREEN: "green", RED: "red"}.get(decision.flag, "orange")
st.markdown(f"## Decision: :{color}[{decision.flag}]")
if p is not None:
    st.metric("Probability of default", f"{p:.1%}")
st.write("**Reasons**")
for r in decision.reasons:
    st.write(f"- {r}")
