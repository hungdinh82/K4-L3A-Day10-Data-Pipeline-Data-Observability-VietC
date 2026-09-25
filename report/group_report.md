# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4-L3A |
| Tên nhóm | VietC |
| Repository | https://github.com/hungdinh82/K4-L3A-Day10-Data-Pipeline-Data-Observability-VietC |
| Ngày hoàn thành | 2026-09-25 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Đinh Văn Hùng | 2A202602443 | Nhóm trưởng | [File, hàm hoặc artifact] |
| 2 | Lê Hoàng Thiên Phú | 2A202602908 | Thành viên | [File, hàm hoặc artifact] |
| 3 | Nguyễn Thanh Phong | 2A202602843 | Thành viên | [File, hàm hoặc artifact] |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành pipeline baseline và luồng corruption–repair cho dữ liệu bài báo từ Crossref. Baseline lấy hoặc tái sử dụng raw snapshot, chuẩn hóa thành 24 bản ghi sạch, lập embedding bằng `sentence-transformers/all-MiniLM-L6-v2`, nạp vào ChromaDB và đánh giá trên bộ 5 câu hỏi cố định. Các artifact đầu ra gồm raw response/records, dữ liệu clean CSV/JSON, embedding/index, test set, metrics, quality/freshness reports và báo cáo Markdown.

Kịch bản corruption đồng thời xóa bốn bản ghi mới nhất, làm rỗng hai summary, chèn nhiễu vào hai embedding text, rút gọn hai title, làm cũ bảy ngày xuất bản và thêm bốn dòng trùng. Tác động rõ nhất là `retrieval_hit_rate` giảm từ 1.0 xuống 0.0; quality gate và freshness đều chuyển từ đạt sang không đạt. Repair dựng lại dữ liệu từ raw snapshot, sau đó re-index và đánh giá lại: retrieval hit rate, token F1, quality và freshness đều phục hồi về mức baseline. Giới hạn chính là LLM Judge có độ biến thiên giữa các lần gọi model, thể hiện ở `judge_accuracy` khác nhau giữa các snapshot baseline.

## 3. Kiến trúc và luồng dữ liệu

```text
Crossref API / raw snapshot
    -> crossref_response.json + crossref_records.json
    -> cleaning và data modeling
    -> papers_clean.csv / papers_clean.json
    -> embedding + ChromaDB collections
    -> evaluation baseline + quality/freshness reports
    -> controlled corruption
    -> corrupted index + re-evaluation
    -> repair từ immutable raw snapshot
    -> repaired index + comparison report
```

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref API hoặc raw snapshot | Query, parse và chuẩn hóa record thô; fallback khi request lỗi | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | [Theo phân công nhóm] |
| Cleaning | Raw records | Chuẩn hóa text/dates, loại thiếu DOI/title/date, bỏ DOI trùng, tạo trường dẫn xuất | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | [Theo phân công nhóm] |
| Embedding/index | Clean/corrupted/repaired dataframe | Embedding bằng MiniLM và tạo collection Chroma tách biệt | `data/embeddings/`, `data/chroma/` | [Theo phân công nhóm] |
| Evaluation | Chroma index và test set cố định | Semantic retrieval, sinh câu trả lời, đo hit rate, token F1 và LLM Judge | `data/results/*_metrics.json`, `*_answers.json` | [Theo phân công nhóm] |
| Observability | Dataframe từng trạng thái | Great Expectations checks và freshness gate | `data/quality/*_quality_report.json`, `*_freshness.json` | [Theo phân công nhóm] |
| Corruption/repair | Clean data và raw snapshot | Tiêm sáu lỗi có kiểm soát; rebuild từ raw snapshot | `corruption_log.json`, clean/embedding repaired artifacts | [Theo phân công nhóm] |
| Orchestration | Settings và các module | Chạy tuần tự baseline hoặc corruption–repair flow | `script/run_phase1.py`, `script/run_corruption_flow.py` | [Theo phân công nhóm] |

## 4. Cách tái hiện kết quả

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `openai` |
| `LLM_MODEL` | `gpt-4o-mini` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày; đạt khi tỷ lệ stale ≤ 25% |
| Random seed | Không cấu hình seed cố định |

Không đưa API key hoặc nội dung `.env` vào báo cáo.

```bash
uv sync
# hoặc khi đã kích hoạt môi trường Python
python -m pip install -e .

python script/run_phase1.py
python script/run_corruption_flow.py
```

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| `python script/run_phase1.py` | Thành công | 2026-09-25 | Log: `Baseline pipeline completed: 24 clean rows`; `data/reports/phase1_report.md` |
| Quality smoke test | Thành công | 2026-09-25 | Log: `Quality check status = True`; `data/quality/test_quality_report.json` |
| Test-set smoke test | Thành công | 2026-09-25 | Log: test set gồm 5 câu hỏi; `data/eval/test_set.json` |
| Retrieval smoke test | Thành công | 2026-09-25 | Log: tìm thấy 2 tài liệu liên quan với `top_k=2` |
| Corruption/repair flow | Có artifacts đầu ra để đối chiếu | 2026-09-25 | `data/results/corruption_log.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

| Thuộc tính | Giá trị |
| --- | --- |
| Source | `https://api.crossref.org/works` |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | `from-pub-date:<ngày chạy - 180 ngày>,has-abstract:true` |
| Snapshot dùng để tái hiện | `data/raw/crossref_records.json` |
| Số record clean | 24 |
| Retry/fallback | Request timeout 30 giây; khi request lỗi, dùng raw response đã lưu nếu có |

| Trường | Kiểu | Bắt buộc | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | string | Có | DOI/document ID | Bỏ record thiếu; chuẩn hóa lowercase; loại trùng theo DOI |
| `title` | string | Có | Tiêu đề bài báo | Chuẩn hóa whitespace; bỏ record thiếu title |
| `summary` | string | Có cho quality gate | Tóm tắt dùng để trả lời | Chuẩn hóa text; quality gate yêu cầu tối thiểu 30 ký tự |
| `published` | ISO date | Có | Ngày xuất bản | Parse lỗi hoặc thiếu thì bỏ record |
| `text_for_embedding` | string | Có | Text đầu vào embedding | Ghép title, authors, published, categories và summary |
| `age_days` | integer | Có | Tuổi dữ liệu tại thời điểm chạy | Tính từ ngày chạy trừ `published` |

Cleaning chuẩn hóa whitespace của title/summary/authors/categories, tạo `authors_joined`, `categories_joined`, `summary_chars`, `age_days` và `text_for_embedding`; sau đó bỏ DOI trùng và sắp xếp theo `published` giảm dần. Document ID chính là DOI đã chuẩn hóa lowercase.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 5 |
| `question_type` | `summary`, `authors`, `date`, `category`, `multi_hop` |
| Ground-truth document ID | DOI của record nguồn; multi-hop dùng hai DOI |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collections | ChromaDB: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM | OpenAI `gpt-4o-mini` |
| Test set dùng chung | `data/eval/test_set.json` |

Test set được giữ nguyên cho baseline, corrupted và repaired để mọi chênh lệch metric phản ánh thay đổi của dữ liệu/index, không phải thay đổi độ khó, câu hỏi hoặc ground truth. Bộ test được load lại nếu file đã tồn tại thay vì tạo lại trong mỗi lần chạy.

## 7. Kết quả baseline

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/` | Có | Crossref response và 24 raw records |
| Cleaned dataset | `data/clean/papers_clean.csv`, `papers_clean.json` | Có | 24 rows |
| Embedding/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | Collection baseline |
| Evaluation set | `data/eval/test_set.json` | Có | 5 câu hỏi |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Ragas được bỏ qua mặc định |
| Quality/freshness | `data/quality/baseline_quality_report.json`, `baseline_freshness.json` | Có | Đều đạt |
| Baseline report | `data/reports/phase1_report.md` | Có | Báo cáo pipeline Pha 1 |

| Metric | Giá trị trong `baseline_metrics.json` | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.0 | Ground-truth document được truy hồi cho toàn bộ 5 câu hỏi |
| `mean_token_f1` | 0.7158 | Mức chồng lấp token trung bình giữa câu trả lời và ground truth |
| `judge_accuracy` | 0.8 | Kết quả baseline gần nhất; có biến thiên do LLM Judge |
| `mean_judge_score` | 3.8 | Điểm Judge trung bình |
| Ragas | N/A | Chưa bật `RUN_RAGAS=1` vì đây là pass chậm hơn |

## 8. Data quality và freshness

| Check | Quality dimension | Ngưỡng/kỳ vọng | Baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| Row count | Completeness | 5–5.000 rows | Pass: 24 | `baseline_quality_report.json` |
| `paper_id`, `title`, `text_for_embedding` not null | Completeness | 0 giá trị bất thường | Pass | `baseline_quality_report.json` |
| `paper_id` unique | Uniqueness | 0 DOI trùng | Pass | `baseline_quality_report.json` |
| `summary` length | Validity | Tối thiểu 30 ký tự | Pass | `baseline_quality_report.json` |

| Thuộc tính | Giá trị baseline |
| --- | --- |
| Freshness đo tại | Clean dataframe trước khi index/serving |
| Ngày xuất bản mới nhất | 2026-07-22 |
| Ngày xuất bản cũ nhất | 2026-03-28 |
| Ngưỡng | 180 ngày; stale ratio tối đa 25% |
| Stale rows | 1/24 (4.17%) |
| Trạng thái | Fresh (`true`) |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Tác động thực tế | Cách repair |
| --- | --- | ---: | --- | --- |
| Drop latest records | Xóa 4 record mới nhất trước khi index | 4 | Làm giảm độ mới của corpus | Rebuild từ raw snapshot |
| Blank summary | Gán summary rỗng | 2 | Vi phạm check độ dài summary | Rebuild từ raw snapshot |
| Inject text noise | Thêm token nhiễu vào `text_for_embedding` | 2 | Làm bẩn nội dung embedding | Rebuild từ raw snapshot |
| Truncate title | Cắt title còn 8 ký tự | 2 | Giảm thông tin retrieval | Rebuild từ raw snapshot |
| Stale date | Đẩy ngày xuất bản lùi 5 năm | 7 | Freshness fail: 8/24 stale rows | Rebuild từ raw snapshot |
| Duplicate rows | Thêm lại 4 dòng đầu | 4 | DOI uniqueness fail: 8 giá trị unexpected | Rebuild từ raw snapshot |

`data/results/corruption_log.json` có đầy đủ 6 loại corruption, số record tác động, DOI liên quan và tham số. Repair không vá trực tiếp corrupted dataframe; pipeline đọc lại immutable `data/raw/crossref_records.json`, chạy cleaning, tạo index repaired và đánh giá lại. Vì vậy output repaired truy vết được về nguồn đáng tin cậy.

## 10. So sánh baseline, corrupted và repaired

Bảng dưới dùng snapshot nhất quán trong `data/reports/corruption_report.md`. `judge_accuracy` của lần chạy baseline sau đó trong `baseline_metrics.json` là 0.8, trong khi snapshot so sánh là 0.6; đây là độ biến thiên của đánh giá dùng LLM.

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0 | 0.0 | 1.0 | -1.0 | +1.0 | Phục hồi hoàn toàn |
| `mean_token_f1` | 0.7158 | 0.4000 | 0.7158 | -0.3158 | +0.3158 | Phục hồi hoàn toàn |
| `judge_accuracy` | 0.6 | 0.4 | 0.6 | -0.2 | +0.2 | Phục hồi về snapshot baseline |
| `mean_judge_score` | 3.8 | 2.6 | 3.6 | -1.2 | +1.0 | Gần baseline nhưng chưa bằng 3.8 |
| Quality checks | Pass | Fail | Pass | Pass → Fail | Fail → Pass | Duplicate DOI và summary rỗng bị phát hiện |
| Freshness | Fresh | Stale | Fresh | Fresh → Stale | Stale → Fresh | Stale ratio: 4.17% → 33.33% → 4.17% |

1. Xóa record mới, làm cũ ngày xuất bản, thêm DOI trùng và làm rỗng summary → quality/freshness gate fail → `retrieval_hit_rate` giảm 1.0 xuống 0.0 và token F1 giảm 0.7158 xuống 0.4.
2. Rebuild clean data từ raw snapshot, re-index và dùng lại test set → quality/freshness pass → retrieval hit rate và token F1 phục hồi đúng mức baseline; mean judge score phục hồi một phần do judge dùng LLM không hoàn toàn xác định.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Các lệnh thử nghiệm có f-string chứa quote/backslash bị `SyntaxError`; quality check chưa chạy được theo lệnh ban đầu.
- **Nguyên nhân:** Backslash xuất hiện bên trong biểu thức f-string (`res[\"success\"]`), điều Python không cho phép; một biến thể dùng nháy đơn/nháy kép lồng nhau cũng bị PowerShell truyền sai quote.
- **Cách xử lý:** Dùng lệnh không có quote lồng trong f-string: `print('Tín hiệu hoàn thành: Quality check status =', res.get('success'))`.
- **Cách xác minh:** Log ngày 2026-09-25 in `Tín hiệu hoàn thành: Quality check status = True`; `data/quality/test_quality_report.json` có `success: true`.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| LLM Judge không cố định | `judge_accuracy`/score thay đổi giữa các lần chạy | Thiết lập temperature 0, lưu model/version/prompt, chạy nhiều lần và báo cáo trung bình/độ lệch chuẩn |
| Ragas mặc định bị tắt | Chưa có metric Ragas để đối chiếu | Bật `RUN_RAGAS=1`, lưu artifact Ragas và đối chiếu cùng test set |
| Source có phụ thuộc thời điểm chạy | Crossref query dùng ngày động, raw snapshot có thể khác khi refresh | Pin snapshot/hashing và ghi timestamp, query/filter vào manifest |
| Chroma artifacts là binary/runtime data | Khó review diff và có thể phình repository | Lưu manifest/version embedding; cân nhắc object storage cho index lớn |

## 13. Checklist trước khi nộp

- [x] Repository và cấu hình không secret đã được ghi nhận.
- [ ] Phân công được nhóm tự hoàn thiện và khớp với module/artifact thực tế.
- [x] Baseline pipeline đã chạy thành công: 24 clean rows.
- [x] Quality smoke test đạt `True`; test set có 5 câu hỏi; retrieval smoke test trả về 2 tài liệu với `top_k=2`.
- [x] Baseline, corrupted và repaired dùng cùng `data/eval/test_set.json`.
- [x] Bảng so sánh có đối chiếu với `data/reports/corruption_report.md`.
- [x] Kết luận quality/freshness có đối chiếu `data/quality/`.
- [x] Có raw, clean, index, metrics, quality/freshness và reports theo cấu trúc bài.
- [ ] Mỗi thành viên hoàn thành báo cáo vai trò riêng và kiểm tra Contributors trên `main`.
- [ ] Rà soát lần cuối để bảo đảm không commit `.env`, API key, token hoặc secret.
