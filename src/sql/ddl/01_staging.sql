-- Staging tables: one per Kaggle CSV, only the columns the warehouse uses.
-- extract.py fills each table by matching column names (case-insensitive) against the CSV header,
-- TRY_CAST-ing every value to the type below; a column missing from the CSV is loaded as NULL
-- (e.g. TARGET in application_test.csv).
-- Need another source column? Add it here and in the transform that uses it.

CREATE OR REPLACE TABLE staging.application (
    sk_id_curr                  BIGINT,
    target                      INTEGER,
    is_train                    BOOLEAN,       -- set by extract.py: train=true, test=false
    name_contract_type          VARCHAR,
    code_gender                 VARCHAR,
    flag_own_car                VARCHAR,
    flag_own_realty             VARCHAR,
    cnt_children                INTEGER,
    amt_income_total            DOUBLE,
    amt_credit                  DOUBLE,
    amt_annuity                 DOUBLE,
    amt_goods_price             DOUBLE,
    name_type_suite             VARCHAR,
    name_income_type            VARCHAR,
    name_education_type         VARCHAR,
    name_family_status          VARCHAR,
    name_housing_type           VARCHAR,
    region_population_relative  DOUBLE,
    days_birth                  INTEGER,
    days_employed               INTEGER,
    days_registration           DOUBLE,
    days_id_publish             INTEGER,
    own_car_age                 DOUBLE,
    occupation_type             VARCHAR,
    cnt_fam_members             DOUBLE,
    region_rating_client        INTEGER,
    region_rating_client_w_city INTEGER,
    weekday_appr_process_start  VARCHAR,
    hour_appr_process_start     INTEGER,
    reg_region_not_live_region  INTEGER,
    reg_region_not_work_region  INTEGER,
    live_region_not_work_region INTEGER,
    reg_city_not_live_city      INTEGER,
    reg_city_not_work_city      INTEGER,
    live_city_not_work_city     INTEGER,
    organization_type           VARCHAR,
    ext_source_1                DOUBLE,
    ext_source_2                DOUBLE,
    ext_source_3                DOUBLE,
    days_last_phone_change      DOUBLE,
    amt_req_credit_bureau_year  DOUBLE
);

CREATE OR REPLACE TABLE staging.bureau (
    sk_id_curr              BIGINT,
    sk_id_bureau            BIGINT,
    credit_active           VARCHAR,
    credit_currency         VARCHAR,
    days_credit             INTEGER,
    credit_day_overdue      INTEGER,
    days_credit_enddate     DOUBLE,
    days_enddate_fact       DOUBLE,
    amt_credit_max_overdue  DOUBLE,
    cnt_credit_prolong      INTEGER,
    amt_credit_sum          DOUBLE,
    amt_credit_sum_debt     DOUBLE,
    amt_credit_sum_limit    DOUBLE,
    amt_credit_sum_overdue  DOUBLE,
    credit_type             VARCHAR,
    days_credit_update      INTEGER,
    amt_annuity             DOUBLE
);

CREATE OR REPLACE TABLE staging.bureau_balance (
    sk_id_bureau    BIGINT,
    months_balance  INTEGER,
    status          VARCHAR   -- C closed, X unknown, 0 no DPD, 1..5 DPD buckets of 30 days
);

CREATE OR REPLACE TABLE staging.previous_application (
    sk_id_prev            BIGINT,
    sk_id_curr            BIGINT,
    name_contract_type    VARCHAR,
    amt_annuity           DOUBLE,
    amt_application       DOUBLE,
    amt_credit            DOUBLE,
    amt_goods_price       DOUBLE,
    name_contract_status  VARCHAR,   -- Approved / Refused / Canceled / Unused offer
    days_decision         INTEGER,
    name_client_type      VARCHAR,
    name_portfolio        VARCHAR,
    name_yield_group      VARCHAR,
    cnt_payment           DOUBLE
);

CREATE OR REPLACE TABLE staging.installments_payments (
    sk_id_prev              BIGINT,
    sk_id_curr              BIGINT,
    num_instalment_version  DOUBLE,
    num_instalment_number   INTEGER,
    days_instalment         DOUBLE,
    days_entry_payment      DOUBLE,
    amt_instalment          DOUBLE,
    amt_payment             DOUBLE
);

CREATE OR REPLACE TABLE staging.pos_cash_balance (
    sk_id_prev             BIGINT,
    sk_id_curr             BIGINT,
    months_balance         INTEGER,
    cnt_instalment         DOUBLE,
    cnt_instalment_future  DOUBLE,
    name_contract_status   VARCHAR,
    sk_dpd                 INTEGER,
    sk_dpd_def             INTEGER
);

CREATE OR REPLACE TABLE staging.credit_card_balance (
    sk_id_prev                 BIGINT,
    sk_id_curr                 BIGINT,
    months_balance             INTEGER,
    amt_balance                DOUBLE,
    amt_credit_limit_actual    DOUBLE,
    amt_drawings_current       DOUBLE,
    amt_payment_total_current  DOUBLE,
    amt_inst_min_regularity    DOUBLE,
    sk_dpd                     INTEGER,
    sk_dpd_def                 INTEGER
);
