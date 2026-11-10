# notebooks/

Nơi làm EDA và thử nghiệm. Đặt tên file theo thứ tự: `01_kpi_eda.ipynb`, `02_profiling.ipynb`.

- Đọc dữ liệu từ kho (`from hcdw.db import get_conn`), không đọc CSV gốc, để cả nhóm dùng chung một bản dữ liệu đã làm sạch.
- Kết quả cuối cùng phải chuyển vào `src/`. Notebook không nằm trong pipeline.
