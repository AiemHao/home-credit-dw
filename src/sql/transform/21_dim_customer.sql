-- staging.application_clean is produced by hcdw/etl/clean.py (nulls, sentinels, buckets).
INSERT INTO dw.dim_customer
SELECT
    ROW_NUMBER() OVER (ORDER BY sk_id_curr)::INTEGER  AS customer_key,
    sk_id_curr,
    gender,
    age_years,
    age_bucket,
    income_type,
    income_bracket,
    education_type,
    family_status,
    housing_type,
    occupation_type,
    organization_type,
    cnt_children,
    CAST(cnt_fam_members AS INTEGER),
    own_car,
    own_realty,
    years_employed,
    is_employed_anomaly
FROM staging.application_clean;
