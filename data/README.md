# data/

| Thư mục | Nội dung | Commit? |
|---|---|---|
| `raw/` | 10 file của Kaggle (~2.5GB), tải bằng `hcdw download` | Không |
| `sample/` | Tập con khoảng 5,000 khách (phân tầng theo TARGET) cùng mọi dòng con liên quan, giữ nguyên tên file và tên cột của Kaggle. Tạo bằng `hcdw sample` | **Có** (đây là dữ liệu mẫu để nộp bài) |
| `fixture/` | Dữ liệu giả để test, tạo bằng `hcdw fixture` | Không |
| `warehouse/` | `hc.duckdb` (kho dữ liệu) + `dq_report.json` | Không |

Nguồn dữ liệu: https://www.kaggle.com/competitions/home-credit-default-risk/data (dùng theo luật của cuộc thi, chỉ cho mục đích học tập).

Chạy lại toàn bộ trên dữ liệu mẫu:

```bash
hcdw etl --source sample
```
