# KPI definitions

Mỗi KPI ghi 4 thông tin: công thức, cột nguồn trong kho, ý nghĩa nghiệp vụ, view SQL tương ứng (`src/sql/marts/50_kpi_views.sql`).
Các dòng dưới đây là **bản nháp**, cần chốt lại khi hoàn thiện mô hình DSS.

| ID | KPI | Công thức | Nguồn | Ý nghĩa | View |
|---|---|---|---|---|---|
| KPI-01 | Default rate | AVG(target), chỉ tính tập train | fact.target | Tỉ lệ khách gặp khó khăn trả nợ | kpi_portfolio_summary, kpi_default_by_segment |
| KPI-02 | Debt-to-income (DTI) | annuity / income (income đã cap) | fact.debt_to_income | Gánh nặng trả góp so với thu nhập | kpi_portfolio_summary |
| KPI-03 | Overdue share | AVG(overdue_flag) | fact.overdue_flag | % khách đang quá hạn ở bureau hoặc từng quá hạn trên 30 ngày | kpi_portfolio_summary |
| KPI-04 | Avg credit amount | AVG(amt_credit) | fact.amt_credit | Quy mô khoản vay | kpi_portfolio_summary |
| KPI-05 | Credit-to-income | credit / income | fact.credit_to_income | Đòn bẩy của khoản vay | kpi_portfolio_summary |

TODO: xác nhận định nghĩa `overdue_flag` (hiện là: đang quá hạn ở bureau, hoặc `max_dpd_days > 30`) và các ngưỡng trong `src/dss/rules.py`.
