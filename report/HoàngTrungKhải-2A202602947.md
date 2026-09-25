# Báo cáo cá nhân - Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Hoàng Trung Khải |
| MSSV | 2A202602947 |
| Khóa/Lớp | K4-L3A |
| Tên nhóm | VietC |
| Vai trò chính | Observability & Evaluation Lead |
| Repository | https://github.com/hungdinh82/K4-L3A-Day10-Data-Pipeline-Data-Observability-VietC |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Quality gate và freshness | `src/observability/quality.py` | DataFrame clean/corrupted/repaired và `Settings` | Quality reports và freshness reports trong `data/quality/` | Hoàn thành |
| Evaluation benchmark | `src/evaluation/testset.py` | Clean DataFrame | `data/eval/test_set.json` gồm 5 mẫu cố định | Hoàn thành |
| Evaluation metrics | `src/evaluation/metrics.py` | Test set, retrieval index và câu trả lời | Hit rate, token F1, Judge và answer artifacts | Hoàn thành |
| Reporting | `src/observability/reporting.py` | Metrics, quality và freshness payloads | `phase1_report.md` và `corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Kiểm tra contract giữa benchmark và pipeline | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` | Baseline, corrupted và repaired dùng cùng `data/eval/test_set.json` |
| Đối chiếu artifact với báo cáo | Ingestion, retrieval và repair | Các kết luận về quality, freshness và metrics có bằng chứng JSON/Markdown |

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Xây dựng quality gate GX 1.x | `src/observability/quality.py` | Kiểm tra row count, null, uniqueness, summary length và freshness | `data/quality/*_quality_report.json` |
| Tạo evaluation set ổn định | `src/evaluation/testset.py` | 5 câu hỏi: summary, authors, date, category và multi-hop | `data/eval/test_set.json` |
| Đo lường RAG | `src/evaluation/metrics.py` | Retrieval hit rate, token F1, Judge accuracy, Judge score | `data/results/*_metrics.json` |
| Tạo báo cáo so sánh | `src/observability/reporting.py` | So sánh baseline/corrupted/repaired | `data/reports/corruption_report.md` |

Kết quả nổi bật là quality gate phát hiện corrupted dataset (`success: false`) và xác nhận repaired dataset đạt lại gate (`success: true`). Retrieval hit rate trên cùng 5 câu hỏi thay đổi `1.0 -> 0.0 -> 1.0` qua ba trạng thái.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần phát hiện cả lỗi dữ liệu cấu trúc và lỗi freshness trước khi dữ liệu đi vào serving layer. Đồng thời, evaluation phải dùng một benchmark cố định để metric giữa baseline, corrupted và repaired có thể so sánh được.

### Cách triển khai

Trong `quality.py`, mỗi trạng thái được kiểm tra bằng Great Expectations 1.x trên ephemeral context. Các expectation kiểm tra số lượng dòng, giá trị null ở các cột bắt buộc, uniqueness của `paper_id` và độ dài `summary` tối thiểu 30 ký tự. `success` của quality report là kết quả kết hợp của toàn bộ expectation và freshness gate.

Freshness đọc `published` và `age_days`, đếm bản ghi vượt ngưỡng 180 ngày, sau đó đạt khi stale ratio không quá 25%. Evaluation set được tạo một lần từ clean DataFrame với ground-truth `paper_id`; pipeline load lại cùng file này cho cả ba trạng thái. Evaluation tính retrieval hit, token F1 và LLM Judge; Ragas được bỏ qua mặc định nếu `RUN_RAGAS` chưa bật.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | DataFrame có `paper_id`, `title`, `summary`, `published`, `age_days`, `text_for_embedding`; test set có `ground_truth_doc_ids` |
| Output | `data/quality/`, `data/eval/test_set.json`, `data/results/*_metrics.json`, `data/results/*_answers.json`, `data/reports/*.md` |
| Module phụ thuộc | `core.config`, `core.utils`, cleaning, retrieval index và QA |
| Module sử dụng output | `phase1.py`, `corruption_flow.py` và báo cáo nhóm |
| Điều kiện lỗi | Null, duplicate DOI, summary quá ngắn, stale ratio vượt SLA, thiếu test set hoặc LLM không khả dụng |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
uv run python -m compileall -q src script
```

- **Kết quả mong đợi:** Baseline và repaired pass; corrupted bị phát hiện; cùng một test set được dùng cho ba trạng thái.
- **Kết quả thực tế:** Baseline `success=true`, corrupted `success=false`, repaired `success=true`; metrics và reports đã được ghi.
- **Artifact:** `data/quality/`, `data/eval/test_set.json`, `data/results/`, `data/reports/`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần so sánh ảnh hưởng của corruption mà không thay đổi độ khó của evaluation.
- **Phương án đã cân nhắc:** Tạo test set riêng cho từng trạng thái hoặc tạo một benchmark ổn định rồi tái sử dụng.
- **Phương án đã chọn:** Tạo và lưu một `data/eval/test_set.json`, sau đó dùng lại cho baseline, corrupted và repaired.
- **Lý do:** Mọi thay đổi metric sẽ phản ánh thay đổi của data/index thay vì thay đổi câu hỏi hoặc ground truth. Mỗi mẫu giữ `ground_truth_doc_ids` để đo retrieval hit.
- **Bằng chứng:** Ba metrics artifacts đều có `samples: 5`; repaired phục hồi retrieval hit rate và mean token F1 về mức baseline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Quality module cần chạy được với Great Expectations 1.x nhưng API datasource, asset và batch khác với các ví dụ phiên bản cũ.
- **Nguyên nhân gốc:** GX 1.x yêu cầu tạo pandas datasource, dataframe asset, batch definition và validate từng expectation theo API mới.
- **Cách xử lý:** Dùng ephemeral context, tạo batch từ DataFrame, validate các expectation chính, kết hợp kết quả với freshness rồi serialize thành JSON.
- **Cách xác minh:** `baseline_quality_report.json` và `repaired_quality_report.json` có `success: true`; corrupted report có `success: false`, freshness `false` và các expectation lỗi được lưu lại.
- **Điều học được:** Observability cần lưu cả boolean tổng hợp và chi tiết từng expectation để truy nguyên nguyên nhân fail.

## 7. Hiểu biết về luồng end-to-end

1. Crossref hoặc raw snapshot đi qua cleaning để tạo clean DataFrame, sau đó được embedding và nạp vào các collection Chroma.
2. Evaluation set lưu câu hỏi, ground truth và DOI đúng. Retrieval hit kiểm tra DOI đúng có xuất hiện trong kết quả; token F1 đo overlap của câu trả lời và LLM Judge chấm tính đúng.
3. Quality checks kiểm tra tính hợp lệ/cấu trúc của DataFrame; freshness theo dõi tuổi của `published` và tỷ lệ bản ghi quá hạn.
4. Dùng cùng test set giúp cô lập tác động của corruption khỏi thay đổi benchmark.
5. Repair thành công khi quality và freshness pass, artifact repaired được tạo lại, đồng thời retrieval và answer metrics phục hồi so với baseline.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.000 | 1.000 | Phục hồi hoàn toàn sau rebuild index |
| `mean_token_f1` | 0.7158 | 0.4000 | 0.7158 | Phục hồi đúng mức baseline |
| `judge_accuracy` | 0.600 | 0.400 | 0.600 | Phục hồi về snapshot baseline |
| `mean_judge_score` | 3.800 | 2.600 | 3.600 | Cải thiện mạnh nhưng chưa bằng baseline |
| Quality checks | Pass | Fail | Pass | Corrupted bị bắt bởi các expectation và freshness |
| Freshness status | Fresh | Stale | Fresh | Stale ratio `4.17% -> 33.33% -> 4.17%` |

### Kết luận từ số liệu

1. Drop record mới, stale date, duplicate và blank summary làm quality/freshness gate fail; retrieval hit rate giảm từ `1.0` xuống `0.0`, token F1 giảm từ `0.7158` xuống `0.4`.
2. Rebuild từ raw snapshot, chạy lại cleaning và re-index làm quality/freshness pass; retrieval hit rate và token F1 phục hồi đúng mức baseline.

Corruption ảnh hưởng rõ nhất là kết hợp drop record mới với stale date: corpus còn 24 dòng nhưng 8 dòng stale, tương đương `33.33%`, vượt SLA 25%. Duplicate và summary rỗng cung cấp thêm tín hiệu lỗi cấu trúc qua uniqueness và summary-length expectations.

Kết quả chưa phục hồi hoàn toàn là `mean_judge_score` (`3.6` so với `3.8`). Nguyên nhân hợp lý là LLM Judge không hoàn toàn deterministic giữa các lần gọi; retrieval hit rate và token F1 cho thấy khả năng phục hồi dữ liệu rõ ràng hơn.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Quality expectation phải gắn với data contract cụ thể, không chỉ kiểm tra số dòng.
2. Freshness là một signal SLA riêng và cần được đọc cùng quality checks.
3. Evaluation chỉ có ý nghĩa khi test set, ground truth và document IDs được giữ ổn định qua các trạng thái.

### Nếu có thêm thời gian

Bổ sung unit tests cho từng expectation và test regression cho test set, đồng thời lưu model/version/prompt/timestamp vào metrics. Có thể chạy LLM Judge nhiều lần để báo cáo trung bình và độ lệch chuẩn thay vì phụ thuộc một snapshot.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hoàng Trung Khải
**Ngày xác nhận:** 2026-09-25
