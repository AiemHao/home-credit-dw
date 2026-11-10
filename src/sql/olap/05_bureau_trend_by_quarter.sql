-- OLAP: time roll-up on fact_bureau_credit (quarter -> year -> all) using dim_time,
-- with the credit status taken from the dim_bureau_category junk dimension.
SELECT
    CASE WHEN GROUPING(t.year) = 1 THEN 'ALL' ELSE CAST(t.year AS VARCHAR) END       AS year,
    CASE WHEN GROUPING(t.quarter) = 1 THEN 'ALL' ELSE 'Q' || t.quarter END           AS quarter,
    COUNT(*)                                                   AS credits_opened,
    COUNT(*) FILTER (WHERE g.credit_active = 'Active')         AS still_active,
    ROUND(SUM(b.amt_credit_sum) / 1e6, 2)                      AS credit_sum_millions
FROM dw.fact_bureau_credit b
JOIN dw.dim_time t            ON t.date_key = b.open_date_key
JOIN dw.dim_bureau_category g USING (bureau_category_key)
GROUP BY ROLLUP (t.year, t.quarter)
ORDER BY GROUPING(t.year), t.year, GROUPING(t.quarter), t.quarter;
