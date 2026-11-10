-- OLAP: CUBE over contract type x gender (every combination of subtotals).
-- GROUPING() = 1 marks a subtotal level; it also sorts the subtotal rows after their members.
SELECT
    CASE WHEN GROUPING(contract_type) = 1 THEN 'ALL' ELSE contract_type END AS contract_type,
    CASE WHEN GROUPING(gender) = 1 THEN 'ALL' ELSE gender END               AS gender,
    COUNT(*)                         AS n_applications,
    ROUND(AVG(target) * 100, 2)      AS default_rate_pct,
    ROUND(MEDIAN(debt_to_income), 3) AS median_dti
FROM mart.v_application_wide
WHERE is_train
GROUP BY CUBE (contract_type, gender)
ORDER BY GROUPING(contract_type), contract_type, GROUPING(gender), gender;
