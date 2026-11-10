-- OLAP: SLICE (cash loans only) + DICE (customers with bureau history, two DPD buckets)
-- then PIVOT the result: credit-history bucket rows x DPD bucket columns.
PIVOT (
    SELECT bureau_active_bucket, max_dpd_bucket, target
    FROM mart.v_application_wide
    WHERE is_train
      AND contract_type = 'Cash loans'
      AND bureau_active_bucket <> 'No bureau record'
)
ON max_dpd_bucket IN ('No DPD', '1-30', '31-60', '61-90', '90+')   -- fixed column order
USING ROUND(AVG(target) * 100, 2)
GROUP BY bureau_active_bucket
ORDER BY bureau_active_bucket;
