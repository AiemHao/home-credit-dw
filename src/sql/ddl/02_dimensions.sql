-- Star schema dimensions. Surrogate keys are assigned in src/sql/transform/2x_*.sql.
-- Placeholders {{...}} are filled by hcdw/etl/load.py from configs/settings.yaml.

-- Calendar built from an ASSUMED snapshot date ({{anchor_date}}): the dataset only has day offsets.
CREATE TABLE dw.dim_time (
    date_key      INTEGER PRIMARY KEY,           -- yyyymmdd
    full_date     DATE    NOT NULL UNIQUE,
    day_offset    INTEGER NOT NULL UNIQUE,       -- days relative to the snapshot (<= 0 is the past)
    month_offset  INTEGER NOT NULL,
    day_of_month  INTEGER NOT NULL CHECK (day_of_month BETWEEN 1 AND 31),
    month_num     INTEGER NOT NULL CHECK (month_num BETWEEN 1 AND 12),
    month_name    VARCHAR NOT NULL,
    quarter       INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    year          INTEGER NOT NULL,
    year_month    VARCHAR NOT NULL,              -- e.g. 2017-03
    is_weekend    BOOLEAN NOT NULL
);

-- One row per applicant (SK_ID_CURR). SCD type 1: the dataset is a single snapshot.
CREATE TABLE dw.dim_customer (
    customer_key         INTEGER PRIMARY KEY,
    sk_id_curr           BIGINT  NOT NULL UNIQUE,
    gender               VARCHAR NOT NULL CHECK (gender IN ('M', 'F', 'Unknown')),
    age_years            DOUBLE  CHECK (age_years BETWEEN 18 AND 100),
    age_bucket           VARCHAR NOT NULL,
    income_type          VARCHAR NOT NULL,       -- employment classification
    income_bracket       VARCHAR NOT NULL,
    education_type       VARCHAR NOT NULL,
    family_status        VARCHAR NOT NULL,
    housing_type         VARCHAR NOT NULL,
    occupation_type      VARCHAR NOT NULL,
    organization_type    VARCHAR NOT NULL,
    cnt_children         INTEGER CHECK (cnt_children >= 0),
    cnt_fam_members      INTEGER CHECK (cnt_fam_members >= 0),
    own_car              BOOLEAN,
    own_realty           BOOLEAN,
    years_employed       DOUBLE  CHECK (years_employed >= 0),
    is_employed_anomaly  BOOLEAN NOT NULL        -- DAYS_EMPLOYED = 365243 sentinel (mostly pensioners)
);

-- Mini-dimension: bucketed credit-history profile built from bureau, bureau_balance,
-- previous_application, installments, POS_CASH and credit card tables.
-- Many applicants share one profile row, which keeps slicing cheap.
CREATE TABLE dw.dim_credit_history (
    credit_history_key    INTEGER PRIMARY KEY,
    bureau_active_bucket  VARCHAR NOT NULL,      -- No bureau record / 0 / 1-2 / 3-5 / 6+
    max_dpd_bucket        VARCHAR NOT NULL,      -- No DPD / 1-30 / 31-60 / 61-90 / 90+
    has_current_overdue   BOOLEAN NOT NULL,
    has_bad_debt          BOOLEAN NOT NULL,
    prev_approval_bucket  VARCHAR NOT NULL,      -- No previous / <50% / 50-99% / 100%
    UNIQUE (bureau_active_bucket, max_dpd_bucket, has_current_overdue, has_bad_debt, prev_approval_bucket)
);

CREATE TABLE dw.dim_contract (
    contract_key    INTEGER PRIMARY KEY,
    contract_type   VARCHAR NOT NULL,            -- Cash loans / Revolving loans
    accompanied_by  VARCHAR NOT NULL,            -- NAME_TYPE_SUITE
    appr_weekday    VARCHAR NOT NULL,
    appr_hour_band  VARCHAR NOT NULL,            -- Night / Morning / Afternoon / Evening
    UNIQUE (contract_type, accompanied_by, appr_weekday, appr_hour_band)
);

-- Junk dimension for the bureau fact: the low-cardinality text codes of a bureau credit, so the
-- fact table keeps only keys and measures (4 statuses x ~15 types x 4 currencies, a few dozen rows).
CREATE TABLE dw.dim_bureau_category (
    bureau_category_key  INTEGER PRIMARY KEY,
    credit_active        VARCHAR NOT NULL,       -- Active / Closed / Sold / Bad debt
    credit_type          VARCHAR NOT NULL,       -- Consumer credit / Credit card / Car loan / Mortgage ...
    credit_currency      VARCHAR NOT NULL,       -- currency 1..4 (anonymised)
    UNIQUE (credit_active, credit_type, credit_currency)
);

CREATE TABLE dw.dim_region (
    region_key                  INTEGER PRIMARY KEY,
    region_rating_client        INTEGER CHECK (region_rating_client BETWEEN 1 AND 3),
    region_rating_city          INTEGER CHECK (region_rating_city BETWEEN 1 AND 3),
    population_density_band     VARCHAR NOT NULL,   -- Low / Medium / High / Unknown
    reg_city_not_live_city      BOOLEAN,
    reg_city_not_work_city      BOOLEAN,
    reg_region_not_live_region  BOOLEAN,
    UNIQUE (region_rating_client, region_rating_city, population_density_band,
            reg_city_not_live_city, reg_city_not_work_city, reg_region_not_live_region)
);
