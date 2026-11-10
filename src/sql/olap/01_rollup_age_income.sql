-- OLAP: ROLL-UP along the customer hierarchy (age bucket -> income bracket -> all).
-- Subtotal rows have NULL in the rolled-up column; GROUPING() tells you which level a row is.
SELECT
    CASE WHEN GROUPING(age_bucket) = 1 THEN 'ALL' ELSE age_bucket END         AS age_bucket,
    CASE WHEN GROUPING(income_bracket) = 1 THEN 'ALL' ELSE income_bracket END AS income_bracket,
    COUNT(*)                         AS n_applications,
    ROUND(AVG(target) * 100, 2)      AS default_rate_pct,
    ROUND(AVG(amt_credit), 0)        AS avg_credit
FROM mart.v_application_wide
WHERE is_train
GROUP BY ROLLUP (age_bucket, income_bracket)
ORDER BY GROUPING(age_bucket), age_bucket, GROUPING(income_bracket), income_bracket;
