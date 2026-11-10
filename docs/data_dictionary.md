# Data dictionary - nguồn Kaggle

Mô tả đầy đủ từng cột nằm trong `HomeCredit_columns_description.csv` (tải cùng bộ dữ liệu; mã hoá latin-1).

| File | Grain | Khoá | Số dòng (full) | Dùng cho |
|---|---|---|---|---|
| application_train.csv | 1 hồ sơ vay, có TARGET | SK_ID_CURR | 307,511 | dim_customer, dim_contract, dim_region, fact_loan_application |
| application_test.csv | 1 hồ sơ vay, không có TARGET | SK_ID_CURR | 48,744 | như trên (`is_train = false`) |
| bureau.csv | 1 khoản tín dụng ở tổ chức khác | SK_ID_BUREAU → SK_ID_CURR | 1,716,428 | fact_bureau_credit, agg_bureau |
| bureau_balance.csv | 1 tháng của 1 khoản bureau | SK_ID_BUREAU, MONTHS_BALANCE | 27,299,925 | agg_bureau_balance |
| previous_application.csv | 1 hồ sơ cũ tại Home Credit | SK_ID_PREV → SK_ID_CURR | 1,670,214 | agg_previous |
| installments_payments.csv | 1 kỳ trả góp | SK_ID_PREV, NUM_INSTALMENT_NUMBER | 13,605,401 | agg_installments |
| POS_CASH_balance.csv | 1 tháng của 1 khoản POS/cash | SK_ID_PREV, MONTHS_BALANCE | 10,001,358 | agg_pos |
| credit_card_balance.csv | 1 tháng của 1 thẻ tín dụng | SK_ID_PREV, MONTHS_BALANCE | 3,840,312 | agg_cc |

Số dòng lấy theo trang dữ liệu của Kaggle. Đối chiếu lại bằng `extracted_rows` trong `dq_report.json`.
