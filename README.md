# Home Credit Data Warehouse & DSS (CO4031 - HK261)

Kho dữ liệu (star schema) + ETL + dashboard OLAP + DSS chấm điểm rủi ro tín dụng trên bộ
[Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk/data).

## Kiến trúc

```
Kaggle CSV (data/raw | data/sample)
   │  extract.py   (DuckDB read_csv, TRY_CAST theo 01_staging.sql)
   ▼
staging.*  ──clean.py (pandas)──► staging.application_clean
   │        ──10_agg_credit_profile.sql──► staging.agg_* (gộp bureau, bureau_balance, previous, installments, POS, credit card)
   ▼  load.py (src/sql/ddl + transform)
dw.dim_* + dw.fact_*   (PK / FK / CHECK)
   ▼  src/sql/marts
mart.v_application_wide, mart.kpi_*      ──► Streamlit dashboard (src/dashboard)
                                          ──► DSS: model + luật Green/Yellow/Red (src/dss)
```

Kho dữ liệu là **DuckDB**: chạy local bằng file `data/warehouse/hc.duckdb`, hoặc trên
**MotherDuck** (DuckDB cloud) để cả nhóm dùng chung. Chọn nơi dùng bằng biến `DW_TARGET` trong `.env`.

## Cài đặt

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
pip install -e ".[etl,dashboard,dev]"
```

Để train mô hình DSS, cài thêm `pip install -e ".[ml]"`. Sau đó `copy .env.example .env`.

## Chạy

| Lệnh | Việc làm |
|---|---|
| `hcdw download` | Tải dữ liệu Kaggle về `data/raw/`. Trước đó phải bấm **I understand and accept** ở tab Rules của cuộc thi và đặt `kaggle.json` vào `~/.kaggle/` |
| `hcdw fixture` | Sinh dữ liệu giả nhỏ vào `data/fixture/` để thử pipeline khi chưa tải dữ liệu thật |
| `hcdw etl --source raw` | Chạy ETL đầy đủ: extract → clean → aggregate → load → kiểm tra chất lượng. `--source` nhận `raw`, `sample`, `fixture` hoặc một thư mục |
| `hcdw sample --n 5000` | Tạo `data/sample/` (dữ liệu mẫu để nộp bài) từ `data/raw/` |
| `hcdw dq` | Chạy lại các bước kiểm tra chất lượng dữ liệu |
| `hcdw olap [01]` | Chạy các truy vấn OLAP mẫu (ROLLUP, CUBE, drill-down, slice/dice, PIVOT, RANK) |
| `hcdw push` | Đẩy kho local lên MotherDuck (cần `MOTHERDUCK_TOKEN`) |
| `hcdw info` | Xem kho đang dùng và số dòng của từng bảng |
| `streamlit run src/dashboard/app.py` | Mở dashboard |
| `python -m dss.train` | Train mô hình DSS |

Lưu ý: với file DuckDB local, chỉ một tiến trình được ghi vào kho. Hãy **tắt dashboard trước khi chạy `hcdw etl`**.

### Dùng chung kho qua MotherDuck
1. Chạy `hcdw etl --source raw --push` (hoặc chạy `hcdw push` sau khi ETL xong).
2. Máy dùng chung đặt `DW_TARGET=motherduck` và `MOTHERDUCK_TOKEN=...` trong `.env`. Dashboard, `dss.train` và `hcdw olap` sẽ đọc thẳng từ cloud, không cần tải 2.5GB dữ liệu.

## Cấu trúc thư mục

| Thư mục | Nội dung |
|---|---|
| `src/sql/ddl/` | Schema `staging` / `dw` / `mart`, DDL star schema có ràng buộc |
| `src/sql/transform/` | `1x` gộp nhiều dòng, `2x` dimension, `3x` fact |
| `src/sql/marts/` | View cho dashboard (`40_`) và KPI (`50_`) |
| `src/sql/olap/` | Truy vấn OLAP mẫu để đưa vào báo cáo |
| `src/hcdw/` | Package Python: config, kết nối DB, ETL, CLI, sample, fixture |
| `src/dashboard/` | Streamlit: trang chủ, các trang 1–3 và 5 (OLAP Explorer) |
| `src/dashboard/pages/4_Risk_Simulator.py` | Trang mô phỏng DSS |
| `src/dss/` | Features, train, predict, luật Green/Yellow/Red |
| `models/` | `model.pkl` (không commit), `metrics.json` |
| `docs/` | `star_schema.md`, `etl_mapping.md`, `kpi_definitions.md` |
| `reports/` | LaTeX báo cáo, hình, slide |
| `notebooks/` | EDA và thử nghiệm |
| `tests/` | pytest trên dữ liệu fixture |
| `data/` | `raw/` và `warehouse/` không commit · `sample/` được commit để nộp bài |


## Kiểm thử

```bash
pytest
```

## Nộp bài (đúng mục 5.1 của đề)
`report.pdf` (lấy từ `reports/latex`) · `src/` · `data/` (chỉ `sample/` và README) · `slides.pdf` · link video đặt ở trang bìa báo cáo.
