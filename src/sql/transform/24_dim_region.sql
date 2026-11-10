INSERT INTO dw.dim_region
SELECT
    ROW_NUMBER() OVER (ORDER BY region_rating_client, region_rating_city, population_density_band,
                                reg_city_not_live_city, reg_city_not_work_city,
                                reg_region_not_live_region)::INTEGER,
    *
FROM (
    SELECT DISTINCT
        region_rating_client,
        region_rating_city,
        population_density_band,
        reg_city_not_live_city,
        reg_city_not_work_city,
        reg_region_not_live_region
    FROM staging.application_clean
);
