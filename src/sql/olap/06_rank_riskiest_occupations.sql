-- OLAP: RANKING with a window function - the 3 riskiest occupations inside each age bucket.
-- Small groups are skipped (n >= 30 labelled applications) so the rate is not just noise.
SELECT
    age_bucket,
    occupation_type,
    n_labelled,
    default_rate_pct,
    rank_in_bucket
FROM (
    SELECT
        age_bucket,
        occupation_type,
        COUNT(*)                                                    AS n_labelled,
        ROUND(AVG(target) * 100, 2)                                 AS default_rate_pct,
        RANK() OVER (PARTITION BY age_bucket ORDER BY AVG(target) DESC) AS rank_in_bucket
    FROM mart.v_application_wide
    WHERE is_train
    GROUP BY age_bucket, occupation_type
    HAVING COUNT(*) >= 30
)
WHERE rank_in_bucket <= 3
ORDER BY age_bucket, rank_in_bucket;
