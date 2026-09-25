# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Lê Hoàng Thiên Phú |
| MSSV | 2A202602908 |
| Khóa/Lớp | K4-L3A |
| Tên nhóm | VietC |
| Vai trò chính | Data Foundation & Recovery |
| Repository | https://github.com/hungdinh82/K4-L3A-Day10-Data-Pipeline-Data-Observability-VietC |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Thu thập và bảo toàn nguồn dữ liệu | `src/ingestion/crossref.py`: `fetch_source_records`, `parse_crossref_payload` | Crossref API hoặc raw response đã lưu | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |
| Làm sạch và mô hình hóa dữ liệu | `src/ingestion/cleaning.py`: `build_clean_dataframe` | Danh sách `PaperRecord` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Hoàn thành |
| Phục hồi dữ liệu | `src/ingestion/corruption.py` và nhánh repair trong `src/pipelines/corruption_flow.py` | Clean data bị corrupt và raw snapshot | `papers_clean_repaired.csv/json`, repaired embeddings/index | Hoàn thành |

Phạm vi của tôi là bảo đảm dữ liệu đi vào các bước embedding, evaluation và observability có nguồn gốc rõ ràng. Các module downstream sử dụng clean dataframe và raw snapshot do phần ingestion/cleaning tạo ra.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Xác minh quality gate sau khi tích hợp | `observability/quality.py` | Chạy smoke test thành công, log trả về `Quality check status = True` |
| Hỗ trợ tái hiện baseline | `script/run_phase1.py` | Pipeline chạy thành công và tạo 24 clean rows |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Chuẩn hóa dữ liệu Crossref | `crossref.py`, `cleaning.py` | 24 bản ghi sạch với DOI, title, summary, published và embedding text | `python script/run_phase1.py` in `Baseline pipeline completed: 24 clean rows` |
| Tạo data contract phục vụ retrieval | `papers_clean.json` | Các trường `paper_id`, `authors_joined`, `categories_joined`, `age_days`, `summary_chars`, `text_for_embedding` | `data/quality/baseline_quality_report.json` pass toàn bộ checks |
| Khôi phục sau corruption | `corruption_flow.py`, `papers_clean_repaired.json` | Dữ liệu repaired có 24 rows, quality và freshness pass | `repaired_quality_report.json` có `success: true` |

Output tôi trực tiếp dùng để kiểm chứng là `data/clean/papers_clean.json`. Artifact này chứa 24 document có `paper_id` duy nhất và `text_for_embedding` đã được dựng từ metadata cùng summary; nó là input cho Chroma index và quality gate.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline RAG không thể đánh giá hoặc phục hồi đáng tin cậy nếu dữ liệu đầu vào thiếu định danh, ngày xuất bản không hợp lệ, hoặc không có raw snapshot để truy vết. Phần việc của tôi giải quyết việc chuyển dữ liệu Crossref không đồng nhất thành một contract ổn định cho embedding, đồng thời giữ nguồn raw để repair không phải sửa trực tiếp dữ liệu lỗi.

### Cách triển khai

`fetch_source_records` gọi Crossref với query về agentic RAG, filter có abstract và thời gian xuất bản; nếu request lỗi thì dùng raw response đã lưu. Parser chuẩn hóa DOI, title, abstract, author, subject và ngày tháng thành `PaperRecord`.

`build_clean_dataframe` loại record không có DOI, title hoặc ngày xuất bản hợp lệ; chuẩn hóa whitespace; chuẩn hóa DOI lowercase; loại trùng theo `paper_id`; rồi tính `age_days`. Hàm tạo các trường hỗ trợ như `authors_joined`, `categories_joined`, `summary_chars` và `text_for_embedding`. Text embedding kết hợp title, authors, published date, categories và summary để giữ ngữ cảnh retrieval.

Trong repair flow, dữ liệu không được sửa từng lỗi trên `corrupted_df`. Thay vào đó, pipeline đọc lại `data/raw/crossref_records.json`, chạy lại cùng quy tắc cleaning, sau đó tạo clean data và index repaired. Cách này idempotent hơn và bảo toàn data lineage.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref payload hoặc raw records JSON; mỗi record cần DOI, title, abstract, metadata ngày tháng nếu hợp lệ |
| Output | Clean dataframe/CSV/JSON gồm metadata chuẩn hóa, `age_days` và `text_for_embedding` |
| Module phụ thuộc | `src/ingestion/crossref.py`, `src/core/config.py`, `src/core/utils.py` |
| Module sử dụng output | `retrieval/index.py`, `evaluation/testset.py`, `observability/quality.py`, `pipelines/corruption_flow.py` |
| Điều kiện lỗi cần xử lý | Request Crossref lỗi, thiếu DOI/title/date, date parse lỗi, DOI trùng |

### Cách xác minh

```bash
python script/run_phase1.py
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print('Tín hiệu hoàn thành: Quality check status =', res.get('success'))"
```

- **Kết quả mong đợi:** Tạo clean data, pipeline baseline hoàn tất và quality gate pass.
- **Kết quả thực tế:** Log ghi `Baseline pipeline completed: 24 clean rows` và `Quality check status = True`.
- **Artifact/log:** `data/clean/papers_clean.json`, `data/quality/baseline_quality_report.json`, `data/quality/test_quality_report.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi corruption xảy ra, có thể sửa trực tiếp các field lỗi trên corrupted dataset hoặc dựng lại từ nguồn raw.
- **Các phương án đã cân nhắc:** (1) Vá từng giá trị summary/date/duplicate trong corrupted dataframe; (2) Đọc raw snapshot, chạy lại cleaning và re-index toàn bộ.
- **Phương án đã chọn:** Phương án 2 — repair từ `data/raw/crossref_records.json`.
- **Lý do:** Sửa trực tiếp có thể bỏ sót lỗi ẩn và không chứng minh được dữ liệu đã trở về đúng nguồn. Rebuild có quy tắc xác định, tái tạo các derived fields nhất quán và có data lineage rõ ràng.
- **Bằng chứng quyết định phù hợp:** Corrupted quality report fail do DOI trùng và summary ngắn; repaired report trở lại `success: true`, 24 rows, unique DOI và freshness `true`. `retrieval_hit_rate` cũng phục hồi từ 0.0 lên 1.0.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `SyntaxError: f-string expression part cannot include a backslash` khi chạy smoke test quality bằng biểu thức `res[\"success\"]` trong f-string.
- **Lệnh hoặc bước tái hiện:** Chạy `python -c` với f-string chứa key dict đã escape bằng backslash trong PowerShell.
- **Nguyên nhân gốc:** Python không cho phép backslash bên trong phần expression của f-string; quote lồng nhau làm chuỗi truyền vào Python không đúng kỳ vọng.
- **Cách xử lý:** Không dùng quote lồng trong f-string, thay bằng `print('Tín hiệu hoàn thành: Quality check status =', res.get('success'))`.
- **Cách xác minh sau khi sửa:** Log trả về `Quality check status = True` và file `data/quality/test_quality_report.json` được tạo với `success: true`.
- **Điều học được:** Với lệnh Python ngắn chạy qua PowerShell, giảm quote lồng nhau giúp câu lệnh ổn định và dễ tái hiện hơn.

## 7. Hiểu biết về luồng end-to-end

1. Crossref response được lưu thành raw response và parse thành raw records. Cleaning chuẩn hóa và tạo clean dataframe; `text_for_embedding` được embedding rồi nạp vào collection ChromaDB tương ứng.
2. Test set chứa câu hỏi, ground truth và DOI ground-truth. Evaluator kiểm tra DOI đúng có nằm trong kết quả retrieval hay không để tính `retrieval_hit_rate`, sau đó so sánh câu trả lời với ground truth bằng token F1 và LLM Judge.
3. Quality checks kiểm tra cấu trúc/nội dung dữ liệu như row count, null, DOI unique và độ dài summary. Freshness monitoring đo `age_days`, tỷ lệ stale và trạng thái SLA; dữ liệu có thể đủ trường nhưng vẫn stale.
4. Giữ nguyên test set loại bỏ biến nhiễu từ câu hỏi/ground truth. Vì vậy khác biệt metric giữa ba trạng thái có thể quy cho thay đổi trong dữ liệu và index.
5. Repair thành công khi rebuilt data xuất phát từ raw snapshot, quality/freshness gate pass lại và các metric retrieval/answer phục hồi. Trong artifact hiện có, hit rate phục hồi 0.0 → 1.0, token F1 0.4 → 0.7158.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0 | 0.0 | 1.0 | Corruption làm mất khả năng truy hồi ground truth; rebuild phục hồi hoàn toàn |
| `mean_token_f1` | 0.7158 | 0.4 | 0.7158 | Chất lượng câu trả lời giảm rồi phục hồi đúng mức baseline |
| `judge_accuracy` | 0.6 | 0.4 | 0.6 | Snapshot so sánh cho thấy phục hồi; baseline chạy riêng có thể dao động 0.8 |
| `mean_judge_score` | 3.8 | 2.6 | 3.6 | Gần baseline sau repair nhưng không hoàn toàn bằng do LLM Judge biến thiên |
| Quality checks | Pass | Fail | Pass | Duplicate DOI và summary rỗng bị gate phát hiện |
| Freshness status | Fresh | Stale | Fresh | Stale ratio: 4.17% → 33.33% → 4.17% |

1. Xóa record mới nhất, tạo ngày cũ, summary rỗng và DOI trùng → freshness/quality chuyển Pass sang Fail → hit rate giảm từ 1.0 xuống 0.0, token F1 giảm từ 0.7158 xuống 0.4.
2. Dựng lại clean data từ raw snapshot và re-index → quality/freshness pass lại → hit rate và token F1 phục hồi đầy đủ; mean judge score phục hồi từ 2.6 lên 3.6.

Corruption ảnh hưởng rõ nhất là tổ hợp các lỗi vì nó đồng thời loại bỏ các document mới có trong test set, làm hỏng nội dung embedding và thêm duplicate. Cần lưu ý không nên kết luận từ riêng judge metric: `judge_accuracy` baseline có snapshot 0.6 trong comparison report nhưng lần baseline gần nhất là 0.8, cho thấy cần kiểm soát tính ngẫu nhiên hoặc chạy lặp khi dùng LLM-as-a-judge.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw snapshot là nền tảng cho reproducibility và repair: có thể dựng lại clean dataset thay vì vá hậu quả của corruption.
2. Data quality và freshness là hai lớp khác nhau: uniqueness/completeness bắt lỗi cấu trúc, còn freshness phát hiện dữ liệu không còn đáp ứng SLA.
3. Chỉ một thay đổi dữ liệu upstream có thể làm retrieval và answer quality suy giảm mạnh dù pipeline không phát sinh exception.

### Nếu có thêm thời gian

Tôi sẽ bổ sung manifest cho raw snapshot gồm timestamp, query/filter, checksum và version embedding. Sau đó chạy `REFRESH_SOURCE=true` trên một bản sao kiểm thử và đối chiếu checksum/row count với snapshot hiện tại. Việc này đo được mức độ thay đổi của nguồn và giúp tái hiện kết quả chính xác hơn.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh vai trò Data Foundation & Recovery và các artifact được kiểm chứng.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module ingestion/cleaning.
- [x] Mọi kết luận metric đều đối chiếu với artifact trong `data/results/` hoặc `data/quality/`.
- [x] Tôi không ghi “đã chạy thành công” cho phần không có log/artifact kèm theo.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này được viết theo phạm vi vai trò cá nhân, không sao chép nguyên văn báo cáo nhóm.

**Họ và tên:** Lê Hoàng Thiên Phú  
**Ngày xác nhận:** 2026-09-25
