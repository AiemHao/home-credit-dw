-- KPI definitions.
-- Every KPI must also be described in docs/kpi_definitions.md (formula, source columns, meaning).
-- Default rate is computed on the training set only (test rows have no TARGET).

-- KPI-01..05: portfolio summary (one row)
CREATE OR REPLACE VIEW mart.kpi_portfolio_summary AS
SELECT
    COUNT(*)                                             AS n_applications,
    COUNT(*) FILTER (WHERE is_train)                     AS n_labelled,
    AVG(target) FILTER (WHERE is_train)                  AS default_rate,          -- KPI-01
    MEDIAN(debt_to_income)                               AS median_debt_to_income, -- KPI-02
    AVG(overdue_flag::INTEGER)                           AS overdue_share,         -- KPI-03
    AVG(amt_credit)                                      AS avg_credit_amount,     -- KPI-04
    MEDIAN(credit_to_income)                             AS median_credit_to_income -- KPI-05
FROM mart.v_application_wide;

-- KPI-01 by segment: default rate per age bucket x income bracket x employment type
CREATE OR REPLACE VIEW mart.kpi_default_by_segment AS
SELECT
    age_bucket,
    income_bracket,
    income_type,
    COUNT(*)            AS n_labelled,
    AVG(target)         AS default_rate,
    MEDIAN(debt_to_income) AS median_debt_to_income
FROM mart.v_application_wide
WHERE is_train
GROUP BY ALL;

-- TODO: add the remaining KPIs from Day 1 (e.g. DTI risk bands, overdue severity mix).
