from dss.rules import GREEN, RED, YELLOW, evaluate


def test_low_risk_is_green():
    assert evaluate({"debt_to_income": 0.1, "max_dpd_days": 0}, 0.03).flag == GREEN


def test_high_dti_is_yellow():
    assert evaluate({"debt_to_income": 0.6, "max_dpd_days": 0}, 0.03).flag == YELLOW


def test_hard_stop_on_long_dpd_is_red():
    assert evaluate({"debt_to_income": 0.1, "max_dpd_days": 120}, 0.03).flag == RED


def test_no_model_means_manual_review():
    assert evaluate({"debt_to_income": 0.1}, None).flag == YELLOW
