# Phân tích yêu cầu nghiệp vụ

Tài liệu này ứng với việc 1 của đề bài: phân tích yêu cầu nghiệp vụ và xác định bài toán. Số liệu thống kê làm căn cứ cho tài liệu này nằm trong [data_profiling.md](data_profiling.md).

## 1. Bối cảnh

Home Credit là một tổ chức tài chính tiêu dùng hoạt động tại nhiều nước Đông Âu và châu Á, trong đó có Việt Nam. Khách hàng chính của Home Credit là những người có ít hoặc không có lịch sử tín dụng. Họ khó vay ở ngân hàng truyền thống vì không đủ dữ liệu để chứng minh khả năng trả nợ.

Với nhóm khách hàng này, quyết định cấp tín dụng luôn phải cân bằng giữa hai loại rủi ro:

- **Duyệt quá lỏng:** khách hàng không trả được nợ, tổ chức mất vốn và chi phí thu hồi nợ tăng.
- **Duyệt quá chặt:** từ chối cả những người có khả năng trả nợ, tổ chức mất doanh thu và khách hàng mất cơ hội tiếp cận tín dụng.

Khi thẩm định thủ công, mỗi hồ sơ được đánh giá theo kinh nghiệm của chuyên viên. Vì vậy kết quả thiếu nhất quán, khó giải thích và khó điều chỉnh đồng loạt khi chính sách rủi ro thay đổi.

Trong khi đó, tổ chức đã có sẵn nhiều dữ liệu lịch sử:
- hồ sơ vay;
- lịch sử tín dụng tại Credit Bureau;
- lịch sử vay và trả nợ tại chính Home Credit.

Các dữ liệu này nằm rải rác ở nhiều bảng và chưa được tổ chức để phân tích hay hỗ trợ quyết định.

### 1.1. Dữ liệu nguồn

Home Credit công bố bộ dữ liệu này cho cuộc thi [Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk) trên Kaggle (2018). Nhóm dùng bản lưu trên Kaggle Datasets: <https://www.kaggle.com/datasets/megancrenshaw/home-credit-default-risk>. Bộ dữ liệu gồm 8 bảng và một file mô tả cột.

| Bảng | Mỗi dòng là |
|---|---|
| `application_train` | Một hồ sơ vay hiện tại: nhân khẩu học, thu nhập, khoản vay, điểm từ nguồn ngoài, nhãn `TARGET` |
| `application_test` | Giống bảng trên nhưng không có `TARGET` |
| `bureau` | Một khoản vay của khách tại tổ chức tín dụng khác (Credit Bureau) |
| `bureau_balance` | Trạng thái quá hạn theo tháng của một khoản vay bureau |
| `previous_application` | Một hồ sơ vay trước đây tại Home Credit: kết quả duyệt, kênh, lý do từ chối |
| `installments_payments` | Một kỳ trả góp: số tiền và ngày phải trả so với thực trả |
| `POS_CASH_balance` | Số dư và số ngày quá hạn theo tháng của khoản vay POS hoặc tiền mặt |
| `credit_card_balance` | Số dư, hạn mức và số ngày quá hạn theo tháng của thẻ tín dụng |

Bảng `application` là trung tâm, với khoá `SK_ID_CURR`. Các bảng lịch sử nối vào qua `SK_ID_CURR`, `SK_ID_PREV` và `SK_ID_BUREAU`.

### 1.2. Đặc điểm dữ liệu ảnh hưởng tới bài toán

- **Nhãn mất cân bằng.** Khách gặp khó khăn trả nợ (`TARGET = 1`) chỉ chiếm một phần nhỏ. Vì vậy không thể đánh giá mô hình bằng độ chính xác (accuracy) thông thường.
- **Không có ngày thực.** Mọi cột thời gian là số ngày hoặc số tháng tính lùi từ lúc nộp hồ sơ. Kho dữ liệu cần một ngày mốc giả định để dựng chiều thời gian.
- **Nhóm khách thiếu lịch sử.** Một phần đáng kể khách hàng không có dữ liệu ở Credit Bureau. Đây chính là nhóm khách hàng đặc thù của Home Credit.
- **Chất lượng dữ liệu.** Có giá trị giả (`DAYS_EMPLOYED = 365243`), giá trị không hợp lệ (giới tính `XNA`), nhiều cột thiếu dữ liệu và thu nhập có ngoại lai.
- **Tập test không có nhãn.** Hồ sơ của `application_test` được dùng như các hồ sơ mới cần thẩm định.

## 2. Phát biểu bài toán

> **Xây dựng kho dữ liệu và hệ hỗ trợ quyết định (DSS) cho thẩm định tín dụng dựa trên phân khúc khách hàng.**
>
> Kho dữ liệu tích hợp hồ sơ vay với toàn bộ lịch sử tín dụng của khách hàng. Nhờ đó có thể phân tích tỷ lệ vỡ nợ theo nhiều chiều.
>
> Với mỗi hồ sơ mới, DSS đánh giá rủi ro từ hai nguồn trên cùng một thang A–E:
> - **hạng điểm:** từ xác suất vỡ nợ (PD) do mô hình ước lượng;
> - **hạng luật:** từ các luật phân khúc và luật nghiệp vụ mà hồ sơ vi phạm.
>
> Hạng cuối là hạng xấu hơn trong hai hạng. Nếu hồ sơ không vi phạm luật nào, hạng cuối là hạng điểm. Mỗi hạng là một phân khúc khách hàng và gắn với đúng một chính sách. Kết quả gồm:
> - hạng cuối của hồ sơ;
> - đề xuất **Duyệt**, **Thẩm định thêm** hoặc **Từ chối**;
> - **hạn mức khuyến nghị**;
> - **lý do** của đề xuất: những yếu tố nào làm tăng rủi ro (theo SHAP) và hồ sơ vi phạm luật nào.

Hệ thống nhằm đạt ba mục tiêu:

1. **Hiểu rủi ro của danh mục:** phân khúc nào có tỷ lệ vỡ nợ cao, chiếm bao nhiêu hồ sơ và bao nhiêu tiền vay.
2. **Ra quyết định nhất quán và giải thích được** cho từng hồ sơ, dựa trên dữ liệu thay vì cảm tính.
3. **Đánh giá trước tác động của chính sách:** khi đổi ngưỡng duyệt thì tỷ lệ duyệt và tỷ lệ vỡ nợ thay đổi ra sao.

Các câu hỏi nghiệp vụ hệ thống phải trả lời được:

| Mã | Câu hỏi |
|---|---|
| Q1 | Tỷ lệ vỡ nợ của danh mục thay đổi thế nào theo tuổi, loại thu nhập, nghề, học vấn, nhà ở, vùng và lịch sử tín dụng? |
| Q2 | Những phân khúc nào rủi ro cao nhất, và chiếm bao nhiêu phần danh mục (số hồ sơ, tổng tiền vay)? |
| Q3 | Lịch sử tín dụng (tại bureau và tại Home Credit) ảnh hưởng thế nào đến khả năng trả nợ? Khách không có lịch sử bureau rủi ro hơn bao nhiêu? |
| Q4 | Một hồ sơ cụ thể có hạng điểm, hạng luật và hạng cuối là gì, nên xử lý ra sao và vì sao? |
| Q5 | Nếu đổi chính sách (ngưỡng hạng, quyết định và hạn mức của từng hạng) thì tỷ lệ duyệt và tỷ lệ vỡ nợ của nhóm được duyệt thay đổi ra sao? |

## 3. Người dùng và quyết định cần hỗ trợ

| Người dùng | Cấp quyết định | Quyết định | Hệ thống hỗ trợ bằng |
|---|---|---|---|
| Trưởng phòng quản lý rủi ro tín dụng | Chiến lược, chiến thuật | Đặt ngưỡng hạng A–E, các luật và chính sách cho từng hạng (quyết định, hạn mức tối đa) | Dashboard danh mục, phân tích OLAP theo hạng và theo các chiều khách hàng, mô phỏng chính sách |
| Chuyên viên thẩm định | Tác nghiệp | Duyệt, chuyển thẩm định thêm hay từ chối một hồ sơ; cho vay bao nhiêu | Trang chấm điểm hồ sơ (PD, hạng điểm, hạng luật, hạng cuối, đề xuất, hạn mức; giải thích bằng SHAP và danh sách luật bị vi phạm); mô phỏng what-if |
| Ban điều hành | Giám sát | Theo dõi sức khoẻ danh mục và hiệu quả của chính sách | Các KPI tổng hợp trên dashboard |

Thẩm định tín dụng là một quyết định **bán cấu trúc** (Turban và cộng sự, 2005):
- Một phần mô hình hoá được bằng dữ liệu, như tỷ lệ vỡ nợ lịch sử và mô hình dự báo.
- Phần còn lại cần phán đoán của con người, ví dụ hồ sơ ở vùng xám hoặc thông tin nằm ngoài hệ thống.

Vì vậy DSS chỉ **đề xuất**, không tự động quyết định. Hồ sơ ở vùng xám được chuyển cho chuyên viên thẩm định thêm.

### 3.1. Các giai đoạn ra quyết định (mô hình Simon)

| Giai đoạn | Hoạt động nghiệp vụ | Thành phần hệ thống |
|---|---|---|
| Nhận thức (Intelligence) | Phát hiện phân khúc và các yếu tố làm tăng rủi ro | Kho dữ liệu, dashboard, truy vấn OLAP |
| Thiết kế (Design) | Xây dựng phương án: thang hạng A–E, ngưỡng hạng, các luật, chính sách cho từng hạng | Mô hình dự báo PD, bảng hạng của luật phân khúc, mô phỏng chính sách |
| Lựa chọn (Choice) | Chọn quyết định cho từng hồ sơ | Hạng cuối của hồ sơ (gộp hạng điểm và hạng luật) và chính sách của hạng đó, kèm lý do |
| Thực hiện (Implementation) | Áp dụng chính sách, theo dõi kết quả | KPI trên dashboard; chạy lại ETL khi có dữ liệu mới |

## 4. Giải pháp: xếp hạng, chính sách và giải thích

### 4.1. Xếp hạng: hạng điểm, hạng luật và hạng cuối

Hệ thống dùng **một thang hạng A–E duy nhất**. Hai nguồn đánh giá đều cho ra hạng trên thang này, rồi được gộp thành **một hạng cuối**:

```
Hồ sơ ─┬─► Điểm rủi ro (PD của mô hình) ──► Hạng điểm ─┐
       │                                                ├─► Hạng cuối = hạng XẤU HƠN ─► Chính sách của hạng
       └─► Các luật ──────────────────────► Hạng luật ─┘                              (quyết định + hạn mức + lý do)
```

**Thang hạng.** Hạng được xác định theo **tỷ lệ rủi ro**, tức xác suất hồ sơ vỡ nợ. Cả hạng điểm và hạng luật đều dùng chung các ngưỡng sau. Mỗi khoảng tính cận dưới, không tính cận trên; ví dụ tỷ lệ rủi ro đúng 7% thuộc hạng C.

| Hạng | Tỷ lệ rủi ro | Ý nghĩa |
|:---:|---|---|
| A | < 1% | Rất tin tưởng |
| B | 1% – 7% | Tin tưởng |
| C | 7% – 13% | Rủi ro vừa phải |
| D | 13% – 20% | Rủi ro cao |
| E | ≥ 20% | Rủi ro rất cao |

Hạng A dành cho những hồ sơ rất tin tưởng nên có ngưỡng chặt nhất (dưới 1%). Hạng E dành cho những hồ sơ có rủi ro từ 20% trở lên. Khoảng 1%–20% ở giữa được chia đều cho ba hạng B, C, D, mỗi hạng rộng khoảng 6–7 điểm phần trăm. Các ngưỡng này là giá trị ban đầu và sẽ được chỉnh bằng mô phỏng chính sách (Q5, BR-09).

**Hạng điểm.** Mô hình ước lượng tỷ lệ rủi ro (PD) của riêng hồ sơ từ dữ liệu trong kho, gồm điểm EXT_SOURCE, khoản vay, thu nhập, lịch sử trả góp, hồ sơ cũ…, và không dùng giới tính. PD được quy về hạng theo bảng trên. PD phải được **hiệu chỉnh (calibration)** để khớp với tỷ lệ vỡ nợ thực tế, vì ngưỡng hạng là xác suất thật.

**Hạng luật.** Luật chỉ dùng để **hạ hạng**: một luật chỉ được tính khi hồ sơ vi phạm luật đó.
- Hạng luật là hạng xấu nhất trong số các luật mà hồ sơ vi phạm.
- Nếu hồ sơ không vi phạm luật nào thì không có hạng luật.
- Tỷ lệ rủi ro của một luật là tỷ lệ vỡ nợ lịch sử của nhóm khách vi phạm luật đó, tức xác suất vỡ nợ của một khách thuộc nhóm. Tỷ lệ này được quy về hạng theo cùng bảng trên, nên mọi luật dùng chung một thang với hạng điểm.

Luật gồm hai nhóm:
- **Luật phân khúc:** dựa trên tỷ lệ vỡ nợ lịch sử của phân khúc khách hàng. Phân khúc được xác định bởi các thuộc tính ổn định, dễ giải thích, ví dụ lịch sử tín dụng, tuổi, nguồn thu nhập, vùng.
- **Luật nghiệp vụ:** dựa trên hành vi tín dụng trong quá khứ, ví dụ bị từ chối nhiều lần hoặc thường xuyên trả trễ.

Danh sách luật cụ thể, các thuộc tính phân khúc và điều kiện vi phạm sẽ được xác định ở phần thiết kế DSS.

**Hạng cuối.**
- Hạng cuối là hạng **xấu hơn** trong hai hạng: hạng điểm và hạng luật.
- Nếu hồ sơ không vi phạm luật nào, hạng cuối chính là hạng điểm.
- Vì vậy hạng A chỉ đạt được khi điểm cá nhân rất tốt **và** hồ sơ không vi phạm luật nào.

Cách gộp này thận trọng và dễ giải thích, ví dụ "hạng điểm B nhưng bị hạ xuống D vì vi phạm một luật hạng D". Vì cách gộp làm tỷ lệ duyệt giảm, các ngưỡng sẽ được chỉnh lại bằng mô phỏng chính sách.

| Hạng điểm | Hạng luật | Hạng cuối | Lý do |
|:---:|:---:|:---:|---|
| A | – | A | Điểm cá nhân rất tốt, không vi phạm luật nào |
| B | D | D | Vi phạm một luật nghiệp vụ hạng D |
| D | – | D | Điểm cá nhân xấu, không vi phạm luật nào |
| B | E | E | Thuộc phân khúc hạng E |

Các thuộc tính phân khúc đồng thời là các chiều phân tích OLAP, ví dụ để trả lời "nhóm nào có nhiều hồ sơ hạng D, E".

### 4.2. Chính sách theo hạng (dự kiến)

| Hạng | Quyết định | Hạn mức tối đa (tiền vay / thu nhập) |
|:---:|---|---|
| A | Duyệt | Cao nhất |
| B | Duyệt | Giảm dần |
| C | Thẩm định thêm | Giảm dần |
| D | Thẩm định thêm | Giảm dần |
| E | Từ chối | – |

Ngưỡng hạng, quyết định và hạn mức cụ thể của từng hạng sẽ được chốt bằng mô phỏng chính sách khi xây dựng DSS. Khi chốt, cần cân bằng giữa tỷ lệ duyệt, tỷ lệ vỡ nợ của nhóm được duyệt và khối lượng hồ sơ phải thẩm định thêm.

### 4.3. Giải thích kết quả

**Người đọc** là chuyên viên thẩm định, tức người review hồ sơ trên trang chấm điểm. Phần giải thích là công cụ nội bộ, không phải văn bản gửi cho khách hàng. Mục đích là giúp chuyên viên:
- hiểu vì sao hệ thống đề xuất như vậy;
- biết cần kiểm tra lại điểm nào, nhất là với hồ sơ Thẩm định thêm;
- tự ra quyết định cuối cùng.

Vì vậy phần giải thích được phép hiển thị thông tin kỹ thuật như tỷ lệ rủi ro, giá trị SHAP và mã luật.

Mỗi kết quả thẩm định phải trả lời được hai câu hỏi: **vì sao hồ sơ bị đánh giá rủi ro**, và **hồ sơ vi phạm luật nào**. Phần giải thích đi theo đúng hai nguồn tạo ra hạng.

**Giải thích hạng điểm bằng SHAP.** SHAP (SHapley Additive exPlanations) chia điểm rủi ro của một hồ sơ thành phần đóng góp của từng yếu tố, so với mức trung bình của danh mục:
- **Yếu tố làm tăng rủi ro** (SHAP dương) là những yếu tố kéo hạng xuống, tức làm hồ sơ "bị trừ điểm".
- **Yếu tố làm giảm rủi ro** (SHAP âm) là những yếu tố kéo hạng lên.
- Trị tuyệt đối của SHAP càng lớn thì yếu tố đó tác động càng mạnh. Giá trị SHAP tính trên thang log-odds, nên chỉ dùng để so sánh các yếu tố với nhau, không đọc thành điểm phần trăm PD.
- Hệ thống hiển thị khoảng 3–5 yếu tố mỗi chiều, có tác động lớn nhất. Mỗi yếu tố ghi tên nghiệp vụ, tên cột trong kho dữ liệu và giá trị của khách, ví dụ "Điểm tín dụng ngoài trung bình (`ext_source_mean`) = 0,21". Nhờ đó chuyên viên đối chiếu được với dữ liệu gốc của hồ sơ.

SHAP được tính trên mô hình trước bước hiệu chỉnh PD. Vì bước hiệu chỉnh giữ nguyên thứ tự rủi ro, chiều tác động của từng yếu tố (tăng hay giảm rủi ro) vẫn đúng với PD sau hiệu chỉnh.

**Giải thích hạng luật.** Hệ thống liệt kê mọi luật mà hồ sơ kích hoạt. Với mỗi luật, ghi rõ mã luật, nhóm vi phạm, tỷ lệ vỡ nợ lịch sử của nhóm đó và hạng tương ứng.

**Giải thích hạng cuối.** Hệ thống nêu nguồn nào quyết định hạng cuối (hạng điểm, hạng luật hay cả hai), và nếu bị hạ hạng thì hạ từ hạng nào xuống hạng nào.

Ví dụ minh hoạ một kết quả thẩm định. Mọi giá trị trong ví dụ chỉ để minh hoạ định dạng:

```
Hồ sơ #100XXX — Hạng cuối: E — Đề xuất: Từ chối

Hạng điểm: C (PD 9,5%)
  Yếu tố làm tăng rủi ro (SHAP, log-odds):
    + Điểm tín dụng ngoài trung bình (ext_source_mean) = 0,21       +0,48
    + Tuổi (age_years) = 28                                         +0,22
    + Số khoản vay đang hoạt động ở bureau (cnt_bureau_active) = 0  +0,15
  Yếu tố làm giảm rủi ro (SHAP, log-odds):
    − Học vấn (education_type) = Higher education                   −0,31
    − Tỷ lệ kỳ trả góp bị trễ (late_payment_ratio) = 0              −0,18

Hạng luật: E
  Luật phân khúc: "Không có bureau | 25–34 | Người làm công | Vùng 3"
    tỷ lệ rủi ro (tỷ lệ vỡ nợ lịch sử của nhóm) 22,8% → E

Hạng cuối: E. Bị hạ từ C xuống E do luật phân khúc.
```

**Giải thích ở cấp danh mục.** Ngoài từng hồ sơ, hệ thống tổng hợp SHAP trên toàn danh mục để cho thấy yếu tố nào ảnh hưởng nhiều nhất tới rủi ro nói chung. Trưởng phòng rủi ro dùng phần này để:
- kiểm tra logic của mô hình có hợp lý về nghiệp vụ không;
- xác nhận giới tính không ảnh hưởng tới kết quả.

## 5. Yêu cầu nghiệp vụ

### 5.1. Yêu cầu chức năng

| Mã | Yêu cầu | Câu hỏi |
|---|---|---|
| BR-01 | Tích hợp 8 bảng nguồn vào kho dữ liệu. Tổng hợp lịch sử tín dụng (bureau, hồ sơ cũ, trả góp, POS, thẻ) về cấp khách hàng | Q1–Q4 |
| BR-02 | Làm sạch và kiểm tra chất lượng dữ liệu (giá trị giả, giá trị thiếu, ngoại lai, ràng buộc khoá). Lưu báo cáo chất lượng sau mỗi lần ETL | – |
| BR-03 | Phân tích danh mục đa chiều: số hồ sơ, tổng tiền vay, tỷ lệ vỡ nợ và phân bố hạng A–E theo các chiều khách hàng, hợp đồng, vùng, lịch sử tín dụng, thời gian. Hỗ trợ roll-up, drill-down, slice, dice, pivot | Q1–Q3 |
| BR-04 | **Hạng điểm:** ước lượng PD đã hiệu chỉnh cho từng hồ sơ bằng mô hình học từ dữ liệu trong kho, rồi quy về hạng A–E theo ngưỡng tỷ lệ rủi ro (mục 4.1) | Q4 |
| BR-05 | **Hạng luật:** lấy hạng xấu nhất trong các luật mà hồ sơ vi phạm; không vi phạm luật nào thì không có hạng luật. Gồm luật phân khúc và luật nghiệp vụ. Hạng của mỗi luật tính từ tỷ lệ vỡ nợ lịch sử của nhóm vi phạm, theo cùng ngưỡng tỷ lệ rủi ro. Danh sách luật cụ thể được xác định ở phần thiết kế DSS | Q2, Q4 |
| BR-06 | **Hạng cuối** là hạng xấu hơn trong hai hạng: hạng điểm và hạng luật. Nếu không vi phạm luật nào, hạng cuối là hạng điểm. Mỗi hạng gắn một chính sách: quyết định (Duyệt / Thẩm định thêm / Từ chối) và hạn mức tối đa (tiền vay / thu nhập) | Q4 |
| BR-07 | Kiểm tra thang hạng: tỷ lệ vỡ nợ thực tế phải tăng đều từ A đến E, cho cả hạng điểm, hạng luật và hạng cuối | Q2 |
| BR-08 | Giải thích mỗi đề xuất cho chuyên viên thẩm định (mục 4.3), gồm ba phần: (1) **SHAP** cho hạng điểm: 3–5 yếu tố làm tăng rủi ro và 3–5 yếu tố làm giảm rủi ro, ghi tên nghiệp vụ, tên cột và giá trị của khách; (2) danh sách **luật bị vi phạm**, kèm tỷ lệ vỡ nợ lịch sử của nhóm vi phạm và hạng của luật; (3) **nguồn quyết định hạng cuối** và mức bị hạ hạng | Q4 |
| BR-09 | Mô phỏng what-if cho một hồ sơ (đổi thu nhập, số tiền vay, …). Mô phỏng chính sách cho cả danh mục: đổi ngưỡng hạng, luật hoặc chính sách của từng hạng thì tỷ lệ duyệt và tỷ lệ vỡ nợ của nhóm được duyệt thay đổi thế nào | Q5 |
| BR-10 | Giao diện web gồm: dashboard tổng quan, phân tích theo hạng, OLAP và trang thẩm định hồ sơ | Q1–Q5 |
| BR-11 | Giải thích cấp danh mục: tổng hợp SHAP trên toàn danh mục để xếp hạng mức ảnh hưởng của các yếu tố, phục vụ kiểm tra logic mô hình và kiểm tra công bằng | Q1, Q3 |

### 5.2. Yêu cầu phi chức năng

- **Hiệu năng:** truy vấn dashboard và chấm điểm một hồ sơ trả kết quả trong vài giây. ETL toàn bộ dữ liệu chạy được trên một máy cá nhân.
- **Tái lập:** dựng lại toàn bộ kho dữ liệu từ dữ liệu gốc bằng một lệnh. Dữ liệu mẫu nộp kèm chạy được với cùng pipeline.
- **Giải thích được:** mọi đề xuất đều kèm lý do, gồm các yếu tố SHAP và các luật bị vi phạm. Kết quả what-if cũng được giải thích lại theo giá trị mới. Các ngưỡng và luật được ghi rõ trong tài liệu.
- **Công bằng:** không dùng giới tính làm căn cứ ra quyết định tín dụng.

## 6. KPI

| Mã | KPI | Công thức và ý nghĩa |
|---|---|---|
| KPI-01 | Tỷ lệ vỡ nợ | Số hồ sơ `TARGET = 1` / số hồ sơ có nhãn. Tính cho cả danh mục, từng hạng và từng nhóm thuộc tính |
| KPI-02 | Phân bố hạng | Số hồ sơ và tỷ trọng của mỗi hạng A–E trong danh mục (theo hạng cuối), kèm % hồ sơ bị hạng luật hạ hạng |
| KPI-03 | Dư nợ cấp mới | Tổng `AMT_CREDIT`, theo hạng hoặc theo nhóm thuộc tính |
| KPI-04 | Dư nợ chịu rủi ro | Σ `AMT_CREDIT` × PD. Ước lượng phần tiền vay có nguy cơ mất |
| KPI-05 | Tỷ lệ rủi ro | Xác suất hồ sơ vỡ nợ: PD đã hiệu chỉnh của hồ sơ, hoặc tỷ lệ vỡ nợ lịch sử của nhóm vi phạm một luật. Là căn cứ xếp hạng A–E cho cả hạng điểm và hạng luật |
| KPI-06 | Tỷ lệ duyệt | Số hồ sơ được đề xuất Duyệt / tổng số hồ sơ, theo chính sách đang mô phỏng |
| KPI-07 | Tỷ lệ vỡ nợ của nhóm được duyệt | Tỷ lệ vỡ nợ thực tế của các hồ sơ được đề xuất Duyệt |
| KPI-08 | Tỷ lệ chuyển thẩm định | Số hồ sơ Thẩm định thêm / tổng số hồ sơ. Đo khối lượng công việc của chuyên viên |
| KPI-09 | Độ phân biệt của mô hình | AUC của mô hình PD trên tập kiểm định |
| KPI-10 | Gánh nặng nợ | Trả góp / thu nhập (DTI) và tiền vay / thu nhập. Chỉ số tham khảo |

## 7. Phạm vi và giả định

**Trong phạm vi:** kho dữ liệu cho 8 bảng nguồn, ETL, phân tích OLAP, dashboard web, DSS thẩm định dựa trên hạng điểm, hạng luật và hạng cuối A–E.

**Ngoài phạm vi:**
- định giá khoản vay (lãi suất);
- tối ưu lợi nhuận;
- quy trình thu hồi nợ;
- cập nhật dữ liệu theo thời gian thực;
- thông báo lý do từ chối cho khách hàng (phần giải thích chỉ dành cho chuyên viên thẩm định).

**Giả định:**

- **Ngày mốc:** mọi hồ sơ được coi là nộp vào ngày 17/05/2018. Các cột ngày và tháng tương đối được quy đổi theo mốc này để dựng chiều thời gian.
- **Ý nghĩa nhãn:** `TARGET = 1` (khách gặp khó khăn trả nợ, theo định nghĩa của Home Credit) được coi là vỡ nợ.
- **Dữ liệu lịch sử và hồ sơ mới:** tập train là dữ liệu lịch sử đã có kết quả, dùng để tính tỷ lệ vỡ nợ và huấn luyện mô hình. Tập test đóng vai trò các hồ sơ mới cần thẩm định.
- **Danh mục:** trong tài liệu này, danh mục là toàn bộ khoản vay lịch sử đã có kết quả trả nợ, tức các hồ sơ trong tập train.
- **Tổn thất:** dữ liệu không có tỷ lệ thu hồi sau vỡ nợ. Vì vậy KPI-04 giả định mất toàn bộ khoản vay khi vỡ nợ, tức một ước lượng thận trọng.
- **Tiền tệ:** số tiền giữ nguyên đơn vị trong dữ liệu gốc, không quy đổi.
- Dữ liệu chỉ dùng cho mục đích học tập, theo điều khoản của nguồn công bố.
