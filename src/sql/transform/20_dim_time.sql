-- Calendar around the assumed snapshot date. The range always covers the oldest bureau credit.
INSERT INTO dw.dim_time
WITH bounds AS (
    SELECT
        LEAST(-{{history_days}}, COALESCE((SELECT MIN(days_credit) FROM staging.bureau), 0)) AS lo,
        {{future_days}} AS hi
),
offsets AS (
    SELECT UNNEST(generate_series(lo, hi))::INTEGER AS day_offset FROM bounds
),
days AS (
    SELECT day_offset, DATE '{{anchor_date}}' + day_offset AS d FROM offsets
)
SELECT
    CAST(strftime(d, '%Y%m%d') AS INTEGER)              AS date_key,
    d                                                   AS full_date,
    day_offset,
    datediff('month', DATE '{{anchor_date}}', d)        AS month_offset,
    dayofmonth(d)                                       AS day_of_month,
    month(d)                                            AS month_num,
    monthname(d)                                        AS month_name,
    quarter(d)                                          AS quarter,
    year(d)                                             AS year,
    strftime(d, '%Y-%m')                                AS year_month,
    dayofweek(d) IN (0, 6)                              AS is_weekend
FROM days
ORDER BY day_offset;
