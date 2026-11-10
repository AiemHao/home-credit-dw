# Kiến trúc & thiết kế

Tài liệu này gom các sơ đồ thiết kế của hệ thống. Mỗi sơ đồ là một file Mermaid trong `docs/diagrams/`;
GitHub vẽ trực tiếp các khối bên dưới, trang **Architecture** của web app vẽ từ chính các file đó và cho tải SVG.
Ảnh PNG cho báo cáo: chạy `python scripts/capture_figures.py` khi `hcdw serve` đang chạy (ra `reports/figures/diagram_*.png`).

Khi sửa sơ đồ: sửa file `.mmd`, rồi chép lại khối tương ứng vào file này.

## 1. Kiến trúc hệ thống

Năm tầng, mỗi tầng một việc: file nguồn → ETL → kho DuckDB (staging / dw / mart) → backend FastAPI (OLAP + DSS) → giao diện React.

```mermaid
flowchart TB
  subgraph SRC["① Source · Kaggle Home Credit Default Risk (8 CSV files, 2.6 GB)"]
    direction LR
    F1["application_train / test<br/>356K loan applications"] ~~~ F2["bureau + bureau_balance<br/>1.7M credits · 27M monthly rows"] ~~~ F3["previous_application · installments<br/>POS_CASH · credit_card"]
  end

  subgraph ETL["② ETL · Python CLI hcdw etl"]
    direction LR
    E1["Extract<br/>CSV → staging"] --> E2["Clean<br/>rules R1–R10"] --> E3["Aggregate<br/>1..N → 1 per applicant"] --> E4["Load<br/>dimensions → facts"] --> E5["Quality gate<br/>keys · FK · reconciliation"]
  end

  subgraph DW["③ Data warehouse · DuckDB file hc.duckdb"]
    direction LR
    S[("staging<br/>typed copies + aggregates")] --> D[("dw<br/>star schema · 6 dims, 2 facts")] --> M[("mart<br/>wide views · KPI views")]
  end

  subgraph BE["④ Backend · FastAPI (hcdw serve)"]
    direction LR
    OLAP["OLAP query layer<br/>roll-up · CUBE · drill · slice/dice · rank"] --> API["REST API /api/*<br/>whitelisted, cached, gzip"]
    DSS["Decision support<br/>LightGBM p(default) + rules"] --> API
  end

  subgraph FE["⑤ Frontend · React + TypeScript + Tailwind + Recharts"]
    direction LR
    P1["Overview<br/>Portfolio"] ~~~ P2["Drill-down<br/>Credit history"] ~~~ P3["OLAP explorer<br/>pivot + saved queries"] ~~~ P4["Risk simulator<br/>Architecture"]
  end

  SRC ==>|"read CSV"| ETL
  ETL ==>|"write hc.duckdb.building, then atomic swap"| DW
  DW ==>|"read-only SQL"| BE
  BE ==>|"HTTP · JSON"| FE
  DW -.->|"hcdw push (optional)"| MD[("MotherDuck<br/>shared cloud copy")]
```

- Kho là một file DuckDB: lưu theo cột, xử lý vector hoá, không cần chạy server. Nạp lại toàn bộ 2,6 GB CSV mất khoảng 40 giây.
- Chỉ API được đọc kho. Trình duyệt không gửi SQL: tên chiều và chỉ số được kiểm tra theo danh sách cho phép, giá trị lọc đi qua tham số.
- MotherDuck là bản sao trên cloud (không bắt buộc) để cả nhóm truy vấn mà không phải tải dữ liệu.

Nguồn: [`docs/diagrams/01_system_architecture.mmd`](diagrams/01_system_architecture.mmd)

## 2. Quy trình ETL

Bảy bước ghi vào file tạm; chỉ khi chạy qua hết mới thay kho đang dùng.

```mermaid
flowchart TB
  RAW["Kaggle CSV files<br/>data/raw (full) · data/sample (5,000 applicants)"] --> X

  subgraph RUN["hcdw etl · writes hc.duckdb.building"]
    direction TB
    X["① Extract · etl/extract.py<br/>read_csv(all_varchar), then TRY_CAST<br/>only the columns declared in ddl/01_staging.sql"]
    C["② Clean · etl/clean.py (pandas)<br/>R1 DAYS_EMPLOYED 365243 → NULL · R2 XNA → Unknown<br/>R4 income outliers capped · R6 age and income buckets<br/>R7 debt-to-income ratios · R10 rating outside 1..3 → NULL"]
    G["③ Aggregate · transform/10_agg_credit_profile.sql<br/>bureau_balance → bureau → applicant<br/>previous apps · installments · POS · credit cards<br/>→ agg_credit_profile, 1 row per applicant"]
    L1["④ Load dimensions · transform/2x_*.sql<br/>dim_time · dim_customer · dim_credit_history<br/>dim_contract · dim_region · dim_bureau_category"]
    L2["⑤ Load facts · transform/3x_*.sql<br/>fact_loan_application · fact_bureau_credit<br/>surrogate-key lookups, FK enforced on insert"]
    MV["⑥ Marts · marts/*.sql<br/>v_application_wide · v_bureau_credit_wide · KPI views"]
    Q{"⑦ Quality · etl/quality.py<br/>PK unique · no orphan FK<br/>row completeness · sum reconciliation"}
    X --> C --> G --> L1 --> L2 --> MV --> Q
  end

  Q -->|"all steps succeeded"| SW["Atomic swap<br/>hc.duckdb.building → hc.duckdb"]
  Q -->|"always"| REP["dq_report.json<br/>row counts · timings · check results"]
  RUN -.->|"any error"| KEEP["Previous hc.duckdb kept unchanged<br/>.building file removed"]
```

- Extract đọc mọi cột dạng chuỗi rồi `TRY_CAST` về kiểu khai báo, nên một giá trị lỗi không làm hỏng cả lần nạp 27 triệu dòng.
- Quy tắc làm sạch R1–R10 viết bằng pandas (dễ đọc, có unit test); phần gộp nặng viết bằng SQL (nhanh).
- Cổng chất lượng: khoá chính, khoá ngoại, đủ số dòng, đối soát tổng tiền giữa staging và fact.

Nguồn: [`docs/diagrams/02_etl_pipeline.mmd`](diagrams/02_etl_pipeline.mmd)

## 3. Star schema (fact constellation)

Hai bảng fact dùng chung dimension khách hàng và thời gian, nên có thể phân tích chéo (drill-across) từ hồ sơ vay sang khoản vay bureau.

```mermaid
erDiagram
    direction LR
    dim_customer ||--o{ fact_loan_application : customer_key
    dim_credit_history ||--o{ fact_loan_application : credit_history_key
    dim_contract ||--o{ fact_loan_application : contract_key
    dim_region ||--o{ fact_loan_application : region_key
    dim_time ||--o{ fact_loan_application : application_date_key
    dim_customer ||--o{ fact_bureau_credit : customer_key
    dim_bureau_category ||--o{ fact_bureau_credit : bureau_category_key
    dim_time ||--o{ fact_bureau_credit : open_date_key
    dim_time |o--o{ fact_bureau_credit : close_date_key

    fact_loan_application {
        bigint application_id PK "SK_ID_CURR"
        int customer_key FK
        int credit_history_key FK
        int contract_key FK
        int region_key FK
        int application_date_key FK
        bool is_train
        int target "1 = payment difficulties"
        double amt_income
        double amt_credit
        double amt_annuity
        double debt_to_income
        double credit_to_income
        double ext_source_mean
        bool overdue_flag
        int cnt_bureau_active
        double prev_approval_rate
        int max_dpd_days
        double late_payment_ratio
    }
    fact_bureau_credit {
        bigint bureau_credit_id PK "SK_ID_BUREAU"
        int customer_key FK
        int bureau_category_key FK
        int open_date_key FK
        int close_date_key FK "NULL while open"
        double amt_credit_sum
        double amt_credit_sum_debt
        double amt_credit_sum_overdue
        int credit_day_overdue
        int credit_duration_days
        int max_bb_dpd_status
        int months_reported
    }
    dim_customer {
        int customer_key PK
        bigint sk_id_curr UK
        varchar gender
        varchar age_bucket
        varchar income_type
        varchar income_bracket
        varchar education_type
        varchar family_status
        varchar occupation_type
        double years_employed
    }
    dim_credit_history {
        int credit_history_key PK "mini-dimension"
        varchar bureau_active_bucket
        varchar max_dpd_bucket
        bool has_current_overdue
        bool has_bad_debt
        varchar prev_approval_bucket
    }
    dim_contract {
        int contract_key PK
        varchar contract_type
        varchar accompanied_by
        varchar appr_weekday
        varchar appr_hour_band
    }
    dim_region {
        int region_key PK
        int region_rating_client
        int region_rating_city
        varchar population_density_band
    }
    dim_bureau_category {
        int bureau_category_key PK "junk dimension"
        varchar credit_active
        varchar credit_type
        varchar credit_currency
    }
    dim_time {
        int date_key PK "yyyymmdd"
        date full_date
        int day_offset UK
        int quarter
        int year
        varchar year_month
    }
```

- Grain: một hồ sơ vay (`SK_ID_CURR`) và một khoản tín dụng bureau (`SK_ID_BUREAU`).
- `dim_credit_history` là mini-dimension: hàng chục triệu dòng lịch sử gộp thành khoảng 200 hồ sơ đã chia bucket.
- `dim_bureau_category` là junk dimension; `dim_time` đóng hai vai trò (ngày mở, ngày tất toán) trên fact bureau.

Nguồn: [`docs/diagrams/03_star_schema.mmd`](diagrams/03_star_schema.mmd)

## 4. Data lineage

Mỗi bảng trong kho đến từ đâu: từ file Kaggle qua staging, bảng gộp, tới bảng của star schema.

```mermaid
flowchart LR
  subgraph SRC["Kaggle files"]
    a1["application_train.csv"]
    a2["application_test.csv"]
    b["bureau.csv"]
    bb["bureau_balance.csv"]
    pa["previous_application.csv"]
    ip["installments_payments.csv"]
    pc["POS_CASH_balance.csv"]
    cc["credit_card_balance.csv"]
  end

  subgraph STG["staging · typed and cleaned"]
    sa["application"]
    sac["application_clean"]
    sb["bureau"]
    sbb["bureau_balance"]
    spa["previous_application"]
    sip["installments_payments"]
    spc["pos_cash_balance"]
    scc["credit_card_balance"]
  end

  subgraph AGG["staging · aggregates"]
    abb["agg_bureau_balance"]
    ab["agg_bureau"]
    ap["agg_previous"]
    ai["agg_installments"]
    apo["agg_pos"]
    ac["agg_cc"]
    prof["agg_credit_profile"]
  end

  subgraph STAR["dw · star schema"]
    dc["dim_customer"]
    dk["dim_contract"]
    dr["dim_region"]
    dch["dim_credit_history"]
    dt["dim_time"]
    dbc["dim_bureau_category"]
    fla[["fact_loan_application"]]
    fbc[["fact_bureau_credit"]]
  end

  a1 --> sa
  a2 --> sa
  sa -->|"clean.py"| sac
  b --> sb
  bb --> sbb
  pa --> spa
  ip --> sip
  pc --> spc
  cc --> scc

  sbb --> abb
  sb --> ab
  abb --> ab
  spa --> ap
  sip --> ai
  spc --> apo
  scc --> ac
  sa --> prof
  ab --> prof
  ap --> prof
  ai --> prof
  apo --> prof
  ac --> prof

  sac --> dc
  sac --> dk
  sac --> dr
  prof --> dch
  sb --> dt
  sb --> dbc
  sac --> fla
  prof --> fla
  sb --> fbc
  abb --> fbc
```

- Các bảng con (1..N dòng mỗi khách) được gộp thành một hồ sơ tín dụng mỗi khách trước khi vào dimension.
- `fact_bureau_credit` giữ grain của bureau và nối về `dim_customer` để phân tích chéo.

Nguồn: [`docs/diagrams/04_data_lineage.mmd`](diagrams/04_data_lineage.mmd)

## 5. Luồng một truy vấn OLAP

Điều gì xảy ra khi người dùng bấm một cột: trạng thái lọc chung → gọi REST → SQL đã kiểm tra → kết quả được cache.

```mermaid
sequenceDiagram
  autonumber
  actor U as Analyst
  participant R as React app (browser)
  participant A as FastAPI /api
  participant Q as Query layer (lru_cache)
  participant D as DuckDB hc.duckdb (read-only)

  U->>R: Pick a filter or click a bar (e.g. age 25-34)
  R->>R: Update the shared filter state (all pages)
  R->>A: GET /api/by/income_type?age_bucket=25-34
  A->>A: Check names against the dimension whitelist (400 if unknown)
  A->>Q: by_dimension(income_type, filters)
  alt result already cached
    Q-->>A: rows from memory
  else first request
    Q->>D: SELECT ... FROM mart.v_application_wide WHERE age_bucket IN (?) GROUP BY 1
    D-->>Q: aggregated rows (vectorised scan, 50-200 ms)
    Q-->>A: rows
  end
  A-->>R: JSON (gzip)
  R-->>U: Charts, KPIs and tables re-render
```

- Kết quả được nhớ theo (truy vấn, bộ lọc). Kho là snapshot tĩnh nên cache không bao giờ cũ cho tới lần ETL sau.
- Truy vấn lần đầu trên 356 nghìn hồ sơ mất 50–200 ms; lần sau dưới 5 ms.

Nguồn: [`docs/diagrams/05_request_flow.mmd`](diagrams/05_request_flow.mmd)

## 6. Luồng hệ hỗ trợ quyết định (DSS)

DSS gộp xác suất vỡ nợ của mô hình và các luật thẩm định thành một quyết định có giải thích.

```mermaid
flowchart LR
  IN["Applicant inputs<br/>income · credit · annuity · age<br/>employment · external score<br/>days past due · bureau credits"] --> F["Feature row<br/>dss/features.py<br/>debt-to-income, credit-to-income"]
  TR["Training · python -m dss.train<br/>labelled rows of mart.v_application_wide"] -.-> MDL
  F --> MDL["LightGBM model<br/>models/model.pkl"]
  MDL --> P{"p(default)"}
  F --> RL["Business rules<br/>dss/rules.py"]
  P -->|"below 8%"| G1["GREEN"]
  P -->|"8% to 20%"| Y1["YELLOW"]
  P -->|"20% or more"| R1["RED"]
  RL -->|"DTI over 0.40 or overdue now"| Y2["YELLOW"]
  RL -->|"history over 90 DPD"| R2["RED"]
  G1 --> W["Strictest outcome wins<br/>+ every reason listed"]
  Y1 --> W
  R1 --> W
  Y2 --> W
  R2 --> W
  W --> OUT(["Approve · Manual review · Reject"])
```

- Mô hình train trên kho (`mart.v_application_wide`), không đọc file gốc, nên dashboard và mô hình thấy cùng một dữ liệu.
- Kết quả khắt khe nhất thắng, và mọi luật bị kích hoạt đều được liệt kê làm lý do.

Nguồn: [`docs/diagrams/06_dss_flow.mmd`](diagrams/06_dss_flow.mmd)

## Công nghệ

| Tầng | Công nghệ |
|---|---|
| Lưu trữ & OLAP | DuckDB (file local) · MotherDuck (bản cloud, không bắt buộc) |
| ETL | Python 3.12 · pandas · DuckDB SQL · CLI Typer (`hcdw`) |
| Backend | FastAPI · Uvicorn · SQL có kiểm tra tên, có cache |
| Frontend | React 18 · TypeScript · Tailwind CSS · Recharts · Mermaid |
| Hỗ trợ quyết định | LightGBM · scikit-learn · luật nghiệp vụ |
| Kiểm thử | pytest (ETL, API) · báo cáo chất lượng mỗi lần chạy |
