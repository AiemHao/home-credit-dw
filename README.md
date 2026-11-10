# Home Credit Data Warehouse & DSS (CO4031 - HK261)

Kho dữ liệu (star schema) + ETL + OLAP + web dashboard + DSS chấm điểm rủi ro tín dụng trên bộ
[Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk/data).

## Kiến trúc

```
Kaggle CSV (data/raw | data/sample)
   │  hcdw etl: extract → clean → aggregate → load → quality   (Python + DuckDB SQL)
   ▼
DuckDB hc.duckdb:  staging.*  →  dw.dim_* + dw.fact_*  →  mart.* (views)
   ▼  read-only SQL
FastAPI (src/hcdw/api)  ──  OLAP query layer + DSS (src/dss)      hcdw serve  → /api/*
   ▼  HTTP JSON
React + TypeScript + Tailwind + Recharts (frontend/)                            → /
```

Sơ đồ chi tiết (kiến trúc hệ thống, ETL, star schema, data lineage, luồng truy vấn, DSS) nằm trong
[docs/architecture.md](docs/architecture.md). Mỗi sơ đồ là một file SVG vẽ tay trong `docs/diagrams/`; trang **Architecture** của web app hiển thị đúng các file đó.

Kho dữ liệu là **DuckDB**: chạy local bằng file `data/warehouse/hc.duckdb`, hoặc trên
**MotherDuck** (DuckDB cloud) để cả nhóm dùng chung. Chọn nơi dùng bằng biến `DW_TARGET` trong `.env`.

## Cài đặt

Python 3.12 và Node.js 20 trở lên.

```bash
python -m venv .venv
```

```bash
.venv/Scripts/pip.exe install -e ".[etl,api,dev]"
```

```bash
cd frontend && npm install && npm run build
```

Để train mô hình DSS, cài thêm `pip install -e ".[ml]"`. Sau đó `copy .env.example .env`.

## Chạy

| Lệnh | Việc làm |
|---|---|
| `hcdw download` | Tải dữ liệu Kaggle về `data/raw/`. Trước đó phải join cuộc thi trên Kaggle và đặt `KAGGLE_API_TOKEN` trong `.env` (hoặc `~/.kaggle/kaggle.json`) |
| `hcdw fixture` | Sinh dữ liệu giả nhỏ vào `data/fixture/` để thử pipeline khi chưa tải dữ liệu thật |
| `hcdw etl --source raw` | Chạy ETL đầy đủ (khoảng 40 giây trên dữ liệu thật). `--source` nhận `raw`, `sample`, `fixture` hoặc một thư mục |
| `hcdw sample --n 5000` | Tạo `data/sample/` (dữ liệu mẫu để nộp bài) từ `data/raw/` |
| `hcdw dq` | Chạy lại các bước kiểm tra chất lượng dữ liệu |
| `hcdw olap [01]` | Chạy các truy vấn OLAP mẫu (ROLLUP, CUBE, drill-down, slice/dice, PIVOT, RANK) |
| `hcdw serve` | Mở web app tại http://127.0.0.1:8000 (API + dashboard đã build). Tài liệu API: `/docs` |
| `hcdw push` | Đẩy kho local lên MotherDuck (cần `MOTHERDUCK_TOKEN`) |
| `hcdw info` | Xem kho đang dùng và số dòng của từng bảng |
| `python scripts/capture_figures.py` | Chụp ảnh các trang và sơ đồ vào `reports/figures/` (cần `hcdw serve` đang chạy) |
| `python -m dss.train` | Train mô hình DSS |

Lưu ý: với file DuckDB local, chỉ một tiến trình được ghi vào kho. Hãy **tắt `hcdw serve` trước khi chạy `hcdw etl`**
(nếu quên, ETL sẽ báo lỗi rõ ràng và kho cũ vẫn giữ nguyên).

### Phát triển giao diện
Chạy hai terminal: `hcdw serve --reload` (API ở cổng 8000) và `cd frontend && npm run dev` (giao diện ở cổng 5173, tự chuyển `/api` sang cổng 8000).

### Dùng chung kho qua MotherDuck
1. Chạy `hcdw etl --source raw --push` (hoặc chạy `hcdw push` sau khi ETL xong).
2. Máy dùng chung đặt `DW_TARGET=motherduck` và `MOTHERDUCK_TOKEN=...` trong `.env`. Web app, `dss.train` và `hcdw olap` sẽ đọc thẳng từ cloud, không cần tải 2,6 GB dữ liệu.

## Cấu trúc thư mục

| Thư mục | Nội dung |
|---|---|
| `src/sql/ddl/` | Schema `staging` / `dw` / `mart`, DDL star schema có ràng buộc |
| `src/sql/transform/` | `1x` gộp nhiều dòng, `2x` dimension, `3x` fact |
| `src/sql/marts/` | View cho web app (`40_`) và KPI (`50_`) |
| `src/sql/olap/` | Truy vấn OLAP mẫu để đưa vào báo cáo |
| `src/hcdw/` | Package Python: config, kết nối DB, ETL, CLI, sample, fixture |
| `src/hcdw/api/` | FastAPI: toàn bộ SQL của web app (`queries.py`) và các endpoint (`app.py`) |
| `frontend/` | React + Tailwind: các trang Overview, Portfolio, Drill-down, Credit history, OLAP explorer, Risk simulator, Architecture |
| `src/dss/` | Features, train, predict, luật Green/Yellow/Red (trang Risk simulator gọi qua `/api/simulator`) |
| `models/` | `model.pkl` (không commit), `metrics.json` |
| `docs/` | `star_schema.md`, `etl_mapping.md`, `architecture.md`, `diagrams/`, `kpi_definitions.md` |
| `reports/` | LaTeX báo cáo, hình, slide |
| `notebooks/` | EDA và thử nghiệm |
| `tests/` | pytest trên dữ liệu fixture (ETL và API) |
| `data/` | `raw/` và `warehouse/` không commit · `sample/` được commit để nộp bài |


## Kiểm thử

```bash
pytest
```

```bash
cd frontend && npm run typecheck
```

## Nộp bài (đúng mục 5.1 của đề)
`report.pdf` (lấy từ `reports/latex`) · `src/` + `frontend/` (không gồm `node_modules`) · `data/` (chỉ `sample/` và README) · `slides.pdf` · link video đặt ở trang bìa báo cáo.
