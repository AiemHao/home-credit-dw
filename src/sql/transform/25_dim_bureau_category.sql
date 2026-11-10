-- Junk dimension: every distinct (status, type, currency) combination seen in the bureau file.
INSERT INTO dw.dim_bureau_category
SELECT
    ROW_NUMBER() OVER (ORDER BY credit_active, credit_type, credit_currency)::INTEGER AS bureau_category_key,
    *
FROM (
    SELECT DISTINCT
        COALESCE(credit_active, 'Unknown')   AS credit_active,
        COALESCE(credit_type, 'Unknown')     AS credit_type,
        COALESCE(credit_currency, 'Unknown') AS credit_currency
    FROM staging.bureau
);
