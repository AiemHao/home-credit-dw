-- Multi-row merges: every child table (1..N rows per applicant) is collapsed to one row per
-- SK_ID_CURR, then combined into staging.agg_credit_profile, which feeds dim_credit_history and
-- the credit measures on fact_loan_application.

-- bureau_balance (monthly status of each bureau credit) -> one row per SK_ID_BUREAU
-- STATUS: 0 = no DPD, 1..5 = DPD buckets of 30 days, C = closed, X = unknown (C/X -> NULL)
CREATE OR REPLACE TABLE staging.agg_bureau_balance AS
SELECT
    sk_id_bureau,
    MAX(TRY_CAST(status AS INTEGER)) AS max_status,
    COUNT(*)                         AS months_reported
FROM staging.bureau_balance
GROUP BY sk_id_bureau;

-- bureau -> one row per applicant
CREATE OR REPLACE TABLE staging.agg_bureau AS
SELECT
    b.sk_id_curr,
    COUNT(*)                                                          AS cnt_bureau_total,
    COUNT(*) FILTER (WHERE b.credit_active = 'Active')                AS cnt_bureau_active,
    COUNT(*) FILTER (WHERE b.credit_active = 'Bad debt')              AS cnt_bureau_bad_debt,
    SUM(CASE WHEN b.credit_active = 'Active' THEN b.amt_credit_sum_debt END) AS sum_active_debt,
    SUM(b.amt_credit_sum_overdue)                                     AS sum_overdue,
    MAX(b.credit_day_overdue)                                         AS max_credit_day_overdue,
    -- "currently overdue" only makes sense for credits that are still open
    SUM(b.amt_credit_sum_overdue) FILTER (WHERE b.credit_active = 'Active') AS sum_active_overdue,
    MAX(b.credit_day_overdue) FILTER (WHERE b.credit_active = 'Active')     AS max_active_day_overdue,
    MAX(bb.max_status)                                                AS max_bb_status
FROM staging.bureau b
LEFT JOIN staging.agg_bureau_balance bb USING (sk_id_bureau)
GROUP BY b.sk_id_curr;

-- previous Home Credit applications -> one row per applicant
CREATE OR REPLACE TABLE staging.agg_previous AS
SELECT
    sk_id_curr,
    COUNT(*)                                                        AS cnt_prev_applications,
    COUNT(*) FILTER (WHERE name_contract_status = 'Approved')       AS cnt_prev_approved,
    COUNT(*) FILTER (WHERE name_contract_status = 'Refused')        AS cnt_prev_refused,
    COUNT(*) FILTER (WHERE name_contract_status = 'Approved')::DOUBLE
        / NULLIF(COUNT(*) FILTER (WHERE name_contract_status IN ('Approved', 'Refused')), 0)
                                                                    AS prev_approval_rate
FROM staging.previous_application
GROUP BY sk_id_curr;

-- installment payment behaviour -> one row per applicant
CREATE OR REPLACE TABLE staging.agg_installments AS
SELECT
    sk_id_curr,
    COUNT(*)                                                         AS cnt_installments,
    COUNT(*) FILTER (WHERE days_entry_payment > days_instalment)     AS cnt_late,
    COUNT(*) FILTER (WHERE days_entry_payment > days_instalment)::DOUBLE / COUNT(*)
                                                                     AS late_payment_ratio,
    GREATEST(MAX(days_entry_payment - days_instalment), 0)::INTEGER  AS max_late_days,
    COUNT(*) FILTER (WHERE amt_payment < amt_instalment)             AS cnt_underpaid
FROM staging.installments_payments
GROUP BY sk_id_curr;

CREATE OR REPLACE TABLE staging.agg_pos AS
SELECT sk_id_curr, MAX(sk_dpd) AS max_pos_dpd
FROM staging.pos_cash_balance
GROUP BY sk_id_curr;

CREATE OR REPLACE TABLE staging.agg_cc AS
SELECT
    sk_id_curr,
    MAX(sk_dpd) AS max_cc_dpd,
    AVG(CASE WHEN amt_credit_limit_actual > 0 THEN amt_balance / amt_credit_limit_actual END)
                AS avg_cc_utilization
FROM staging.credit_card_balance
GROUP BY sk_id_curr;

-- One credit profile per applicant (every applicant gets a row, even without history)
CREATE OR REPLACE TABLE staging.agg_credit_profile AS
WITH base AS (
    SELECT
        a.sk_id_curr,
        b.sk_id_curr IS NOT NULL                     AS has_bureau,
        COALESCE(b.cnt_bureau_active, 0)             AS cnt_bureau_active,
        COALESCE(b.cnt_bureau_bad_debt, 0) > 0       AS has_bad_debt,
        COALESCE(b.sum_active_overdue, 0) > 0
            OR COALESCE(b.max_active_day_overdue, 0) > 0
                                                     AS has_current_overdue,
        GREATEST(
            COALESCE(b.max_credit_day_overdue, 0),
            CASE b.max_bb_status WHEN 1 THEN 1 WHEN 2 THEN 31 WHEN 3 THEN 61
                                 WHEN 4 THEN 91 WHEN 5 THEN 121 ELSE 0 END,
            COALESCE(i.max_late_days, 0),
            COALESCE(p.max_pos_dpd, 0),
            COALESCE(c.max_cc_dpd, 0)
        )::INTEGER                                   AS max_dpd_days,
        COALESCE(pr.cnt_prev_applications, 0)        AS cnt_prev_applications,
        pr.prev_approval_rate,
        i.late_payment_ratio,
        c.avg_cc_utilization
    FROM staging.application a
    LEFT JOIN staging.agg_bureau       b  ON b.sk_id_curr  = a.sk_id_curr
    LEFT JOIN staging.agg_installments i  ON i.sk_id_curr  = a.sk_id_curr
    LEFT JOIN staging.agg_pos          p  ON p.sk_id_curr  = a.sk_id_curr
    LEFT JOIN staging.agg_cc           c  ON c.sk_id_curr  = a.sk_id_curr
    LEFT JOIN staging.agg_previous     pr ON pr.sk_id_curr = a.sk_id_curr
)
SELECT
    *,
    -- Draft KPI definition (to confirm in docs/kpi_definitions.md):
    -- overdue = overdue right now in the bureau, or ever more than 30 days past due anywhere
    has_current_overdue OR max_dpd_days > 30         AS overdue_flag,
    CASE
        WHEN NOT has_bureau          THEN 'No bureau record'
        WHEN cnt_bureau_active = 0   THEN '0'
        WHEN cnt_bureau_active <= 2  THEN '1-2'
        WHEN cnt_bureau_active <= 5  THEN '3-5'
        ELSE '6+'
    END                                              AS bureau_active_bucket,
    CASE
        WHEN max_dpd_days = 0   THEN 'No DPD'
        WHEN max_dpd_days <= 30 THEN '1-30'
        WHEN max_dpd_days <= 60 THEN '31-60'
        WHEN max_dpd_days <= 90 THEN '61-90'
        ELSE '90+'
    END                                              AS max_dpd_bucket,
    CASE
        WHEN cnt_prev_applications = 0  THEN 'No previous'
        WHEN prev_approval_rate IS NULL THEN 'No decision'
        WHEN prev_approval_rate < 0.5   THEN '<50%'
        WHEN prev_approval_rate < 1     THEN '50-99%'
        ELSE '100%'
    END                                              AS prev_approval_bucket
FROM base;
