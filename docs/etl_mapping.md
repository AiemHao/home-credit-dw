# ETL mapping

Tài liệu này dùng cho Chương 2 (Data Warehouse & ETL Mapping). Số dòng và thời gian chạy thật lấy trong `data/warehouse/dq_report.json` sau khi chạy `hcdw etl --source raw`.

## Các bước
| Bước | Code | Input → Output |
|---|---|---|
| Extract | `src/hcdw/etl/extract.py` + `ddl/01_staging.sql` | 8 file CSV → `staging.*` (chỉ lấy cột cần dùng, `TRY_CAST` theo kiểu khai báo) |
| Clean | `src/hcdw/etl/clean.py` | `staging.application` → `staging.application_clean` |
| Aggregate | `transform/10_agg_credit_profile.sql` | bảng con 1..N dòng → `staging.agg_*` (1 dòng/khách) |
| Load dims | `transform/2x_*.sql` | staging → `dw.dim_*` |
| Load facts | `transform/3x_*.sql` | staging + dims → `dw.fact_*` |
| Marts | `marts/*.sql` | dw → `mart.*` views |
| Quality | `src/hcdw/etl/quality.py` | dw → `dq_report.json` |
| Publish | `src/hcdw/etl/pipeline.py` | Mọi bước trên ghi vào `hc.duckdb.building`. Chạy xong mới thay `hc.duckdb`; nếu lỗi, kho cũ giữ nguyên |

## Quy tắc làm sạch (clean.py)
| # | Quy tắc | Cột |
|---|---|---|
| R1 | `DAYS_EMPLOYED = 365243` là giá trị sentinel (phần lớn là người hưu trí) → NULL, bật cờ `is_employed_anomaly` | DAYS_EMPLOYED |
| R2 | `XNA` / `Unknown` / rỗng → `'Unknown'` | các cột phân loại |
| R3 | Giới tính khác M/F → `'Unknown'` | CODE_GENDER |
| R4 | Thu nhập > quantile 99.9% → bật cờ `is_income_outlier`, dùng thu nhập đã cap khi tính các tỉ lệ | AMT_INCOME_TOTAL |
| R5 | `age_years = -DAYS_BIRTH/365.25`, `years_employed = -DAYS_EMPLOYED/365.25` | |
| R6 | Chia bucket tuổi và thu nhập theo `configs/settings.yaml` | |
| R7 | `debt_to_income = annuity/income`, `credit_to_income`, `credit_to_goods` | |
| R8 | `ext_source_mean` = trung bình các EXT_SOURCE có giá trị | EXT_SOURCE_1..3 |
| R9 | Tạo `appr_hour_band` và `population_density_band`; đổi cờ 0/1 sang boolean | |
| R10 | Hạng vùng ngoài miền 1..3 → NULL (`application_test` có một giá trị -1) | REGION_RATING_CLIENT(_W_CITY) |

## Gộp nhiều dòng (10_agg_credit_profile.sql)
| Nguồn | Gộp theo | Chỉ số |
|---|---|---|
| bureau_balance | SK_ID_BUREAU | `max_status` (STATUS 1..5 = DPD theo khoảng 30 ngày; C và X → NULL), `months_reported` |
| bureau (+ agg_bureau_balance) | SK_ID_CURR | số khoản đang active, số khoản bad debt, tổng nợ, tổng quá hạn, max ngày quá hạn, max status. "Đang quá hạn" (`has_current_overdue`) chỉ tính trên khoản **Active**: khoản đã đóng mà còn số quá hạn là dữ liệu cũ, không phải nợ hiện tại |
| previous_application | SK_ID_CURR | số hồ sơ cũ, tỉ lệ được duyệt = Approved / (Approved + Refused) |
| installments_payments | SK_ID_CURR | tỉ lệ trả trễ, số ngày trễ tối đa, số kỳ trả thiếu |
| POS_CASH_balance / credit_card_balance | SK_ID_CURR | max SK_DPD, mức sử dụng hạn mức thẻ |
| → agg_credit_profile | SK_ID_CURR | `max_dpd_days` = max các nguồn trên; `overdue_flag`; các bucket của mini-dimension |

## Ánh xạ cột chính: nguồn → đích
| Nguồn (Kaggle) | Đích | Quy tắc |
|---|---|---|
| application_*.SK_ID_CURR | fact_loan_application.application_id, dim_customer.sk_id_curr | |
| application_train.TARGET | fact_loan_application.target | Tập test → NULL |
| AMT_INCOME_TOTAL | fact.amt_income, dim_customer.income_bracket | R4, R6 |
| AMT_ANNUITY / AMT_INCOME_TOTAL | fact.debt_to_income | R7 |
| DAYS_BIRTH | dim_customer.age_years, age_bucket | R5, R6 |
| DAYS_EMPLOYED | dim_customer.years_employed, is_employed_anomaly | R1, R5 |
| NAME_INCOME_TYPE | dim_customer.income_type | R2 |
| NAME_CONTRACT_TYPE | dim_contract.contract_type | R2 |
| REGION_RATING_CLIENT(_W_CITY) | dim_region.region_rating_client / _city | |
| bureau.DAYS_CREDIT | fact_bureau_credit.open_date_key | snapshot + DAYS_CREDIT, tra theo `dim_time.day_offset` |
| bureau.DAYS_ENDDATE_FACT | fact_bureau_credit.close_date_key, credit_duration_days | snapshot + DAYS_ENDDATE_FACT; NULL nếu ngoài lịch hoặc trước ngày mở |
| bureau.CREDIT_ACTIVE / CREDIT_TYPE / CREDIT_CURRENCY | dim_bureau_category (→ fact.bureau_category_key); CREDIT_ACTIVE còn dùng cho dim_credit_history.bureau_active_bucket | NULL → `'Unknown'` |

## Kiểm tra chất lượng
| Nhóm | Kiểm tra | Fail thì ETL báo lỗi? |
|---|---|:-:|
| Khoá | PK không trùng, không NULL (mọi bảng `dw`) · không có FK mồ côi (FK cho phép NULL thì bỏ qua NULL) | ✓ |
| Đầy đủ | số dòng fact = số dòng `staging.application` · số dòng `fact_bureau_credit` = số dòng bureau nạp được (có khách, có ngày mở) | ✓ |
| Đối soát | tổng `AMT_CREDIT` ở staging = ở fact · tổng `AMT_CREDIT_SUM` bureau ở staging = ở fact | ✓ |
| Nghiệp vụ | TARGET chỉ có ở tập train | ✓ |
| Thông tin (`info:`) | tỉ lệ bản ghi bureau được nạp · tỉ lệ khoản đã đóng có ngày tất toán dùng được · default rate tập train · tỉ lệ NULL của các measure | luôn pass |

Ngoài ra ràng buộc PK / FK / CHECK / NOT NULL trong DDL chặn dữ liệu sai ngay lúc INSERT.
