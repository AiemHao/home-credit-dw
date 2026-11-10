-- Fact tables. Dimensions must be loaded first (FKs are enforced on insert).

-- Grain: one loan application (SK_ID_CURR). Train rows carry TARGET; test rows have
-- TARGET NULL and is_train = false so the DSS can score them.
CREATE TABLE dw.fact_loan_application (
    application_id        BIGINT  PRIMARY KEY,                -- SK_ID_CURR (degenerate)
    customer_key          INTEGER NOT NULL REFERENCES dw.dim_customer (customer_key),
    credit_history_key    INTEGER NOT NULL REFERENCES dw.dim_credit_history (credit_history_key),
    contract_key          INTEGER NOT NULL REFERENCES dw.dim_contract (contract_key),
    region_key            INTEGER NOT NULL REFERENCES dw.dim_region (region_key),
    application_date_key  INTEGER NOT NULL REFERENCES dw.dim_time (date_key),
    is_train              BOOLEAN NOT NULL,
    target                INTEGER CHECK (target IN (0, 1)),   -- 1 = client with payment difficulties
    amt_income            DOUBLE  NOT NULL CHECK (amt_income > 0),
    amt_credit            DOUBLE  NOT NULL CHECK (amt_credit > 0),
    amt_annuity           DOUBLE  CHECK (amt_annuity >= 0),
    amt_goods_price       DOUBLE  CHECK (amt_goods_price >= 0),
    debt_to_income        DOUBLE,     -- annuity / income (capped income)
    credit_to_income      DOUBLE,     -- credit / income (capped income)
    credit_to_goods       DOUBLE,     -- credit / goods price
    ext_source_mean       DOUBLE CHECK (ext_source_mean BETWEEN 0 AND 1),
    overdue_flag          BOOLEAN NOT NULL,   -- any current overdue in bureau or any DPD history
    cnt_bureau_active     INTEGER NOT NULL DEFAULT 0,
    cnt_prev_applications INTEGER NOT NULL DEFAULT 0,
    prev_approval_rate    DOUBLE CHECK (prev_approval_rate BETWEEN 0 AND 1),
    max_dpd_days          INTEGER NOT NULL DEFAULT 0,
    late_payment_ratio    DOUBLE CHECK (late_payment_ratio BETWEEN 0 AND 1)
);

-- Grain: one credit reported by the Credit Bureau (SK_ID_BUREAU).
-- Shares dim_customer and dim_time with the application fact (fact constellation), and is the
-- fact that gives dim_time real meaning: credits opened per month, by status / type.
-- dim_time plays two roles here: open date (always known) and actual close date (closed credits only).
CREATE TABLE dw.fact_bureau_credit (
    bureau_credit_id        BIGINT  PRIMARY KEY,               -- SK_ID_BUREAU (degenerate)
    customer_key            INTEGER NOT NULL REFERENCES dw.dim_customer (customer_key),
    bureau_category_key     INTEGER NOT NULL REFERENCES dw.dim_bureau_category (bureau_category_key),
    open_date_key           INTEGER NOT NULL REFERENCES dw.dim_time (date_key),
    close_date_key          INTEGER REFERENCES dw.dim_time (date_key),  -- NULL: still open or date unusable
    amt_credit_sum          DOUBLE,
    amt_credit_sum_debt     DOUBLE,
    amt_credit_sum_overdue  DOUBLE,
    credit_day_overdue      INTEGER NOT NULL DEFAULT 0 CHECK (credit_day_overdue >= 0),
    credit_duration_days    INTEGER CHECK (credit_duration_days >= 0),  -- close - open, closed credits only
    max_bb_dpd_status       INTEGER CHECK (max_bb_dpd_status BETWEEN 0 AND 5),
    months_reported         INTEGER NOT NULL DEFAULT 0
);
