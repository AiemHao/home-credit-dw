-- Mini-dimension: one row per distinct bucketed profile (a few hundred rows at most).
INSERT INTO dw.dim_credit_history
SELECT
    ROW_NUMBER() OVER (ORDER BY bureau_active_bucket, max_dpd_bucket, has_current_overdue,
                                has_bad_debt, prev_approval_bucket)::INTEGER AS credit_history_key,
    *
FROM (
    SELECT DISTINCT
        bureau_active_bucket,
        max_dpd_bucket,
        has_current_overdue,
        has_bad_debt,
        prev_approval_bucket
    FROM staging.agg_credit_profile
);
