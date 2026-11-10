-- OLAP: DRILL-DOWN from one age bucket into employment type, then occupation.
-- Change the slice value to drill into another member.
SELECT
    income_type,
    occupation_type,
    COUNT(*)                    AS n_applications,
    ROUND(AVG(target) * 100, 2) AS default_rate_pct
FROM mart.v_application_wide
WHERE is_train
  AND age_bucket = '25-34'
GROUP BY income_type, occupation_type
HAVING COUNT(*) >= 30
ORDER BY default_rate_pct DESC;
