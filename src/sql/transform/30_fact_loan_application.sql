-- Surrogate-key lookups use IS NOT DISTINCT FROM so NULL attributes still match their dim row.
INSERT INTO dw.fact_loan_application
SELECT
    a.sk_id_curr                                           AS application_id,
    c.customer_key,
    h.credit_history_key,
    k.contract_key,
    r.region_key,
    -- No real application date exists: every application sits on the snapshot date.
    CAST(strftime(DATE '{{anchor_date}}', '%Y%m%d') AS INTEGER) AS application_date_key,
    a.is_train,
    a.target,
    a.amt_income_total,
    a.amt_credit,
    a.amt_annuity,
    a.amt_goods_price,
    a.debt_to_income,
    a.credit_to_income,
    a.credit_to_goods,
    a.ext_source_mean,
    p.overdue_flag,
    p.cnt_bureau_active,
    p.cnt_prev_applications,
    p.prev_approval_rate,
    p.max_dpd_days,
    p.late_payment_ratio
FROM staging.application_clean a
JOIN dw.dim_customer c         ON c.sk_id_curr = a.sk_id_curr
JOIN staging.agg_credit_profile p ON p.sk_id_curr = a.sk_id_curr
JOIN dw.dim_credit_history h
     ON  h.bureau_active_bucket = p.bureau_active_bucket
     AND h.max_dpd_bucket       = p.max_dpd_bucket
     AND h.has_current_overdue  = p.has_current_overdue
     AND h.has_bad_debt         = p.has_bad_debt
     AND h.prev_approval_bucket = p.prev_approval_bucket
JOIN dw.dim_contract k
     ON  k.contract_type  = a.contract_type
     AND k.accompanied_by = a.accompanied_by
     AND k.appr_weekday   = a.appr_weekday
     AND k.appr_hour_band = a.appr_hour_band
JOIN dw.dim_region r
     ON  r.region_rating_client       IS NOT DISTINCT FROM a.region_rating_client
     AND r.region_rating_city         IS NOT DISTINCT FROM a.region_rating_city
     AND r.population_density_band    =                    a.population_density_band
     AND r.reg_city_not_live_city     IS NOT DISTINCT FROM a.reg_city_not_live_city
     AND r.reg_city_not_work_city     IS NOT DISTINCT FROM a.reg_city_not_work_city
     AND r.reg_region_not_live_region IS NOT DISTINCT FROM a.reg_region_not_live_region;
