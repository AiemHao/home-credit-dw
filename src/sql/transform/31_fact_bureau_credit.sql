-- open_date  = snapshot date + DAYS_CREDIT       (DAYS_CREDIT is negative: days before the application)
-- close_date = snapshot date + DAYS_ENDDATE_FACT (closed credits only)
-- Both dates are looked up in dim_time by day_offset, so a key always points at an existing row.
-- A close date outside the calendar (the source has a few absurd values, e.g. 100+ years ago) or
-- before the open date is treated as unusable and left NULL.
INSERT INTO dw.fact_bureau_credit
SELECT
    b.sk_id_bureau,
    c.customer_key,
    g.bureau_category_key,
    t_open.date_key                                              AS open_date_key,
    t_close.date_key                                             AS close_date_key,
    b.amt_credit_sum,
    b.amt_credit_sum_debt,
    b.amt_credit_sum_overdue,
    GREATEST(COALESCE(b.credit_day_overdue, 0), 0),
    CASE WHEN t_close.date_key IS NOT NULL
         THEN (b.days_enddate_fact - b.days_credit)::INTEGER END AS credit_duration_days,
    bb.max_status,
    COALESCE(bb.months_reported, 0)
FROM staging.bureau b
JOIN dw.dim_customer c USING (sk_id_curr)
JOIN dw.dim_bureau_category g
     ON  g.credit_active   = COALESCE(b.credit_active, 'Unknown')
     AND g.credit_type     = COALESCE(b.credit_type, 'Unknown')
     AND g.credit_currency = COALESCE(b.credit_currency, 'Unknown')
JOIN dw.dim_time t_open ON t_open.day_offset = b.days_credit
LEFT JOIN dw.dim_time t_close
     ON  t_close.day_offset = b.days_enddate_fact::INTEGER
     AND b.days_enddate_fact >= b.days_credit
LEFT JOIN staging.agg_bureau_balance bb USING (sk_id_bureau)
WHERE b.sk_id_bureau IS NOT NULL;
