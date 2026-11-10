INSERT INTO dw.dim_contract
SELECT
    ROW_NUMBER() OVER (ORDER BY contract_type, accompanied_by, appr_weekday, appr_hour_band)::INTEGER,
    *
FROM (
    SELECT DISTINCT contract_type, accompanied_by, appr_weekday, appr_hour_band
    FROM staging.application_clean
);
