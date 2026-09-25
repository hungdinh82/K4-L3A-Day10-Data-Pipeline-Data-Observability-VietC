# Báo cáo vai trò thành viên — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Thanh Phong |
| MSSV | 2A202602843 |
| Khóa/Lớp | K4-L3A |
| Tên nhóm | VietC |
| Vai trò chính | Data Foundation & Recovery |
| Repository | https://github.com/hungdinh82/K4-L3A-Day10-Data-Pipeline-Data-Observability-VietC |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

Vai trò của tôi là xây dựng nền dữ liệu đầu vào ổn định cho toàn bộ pipeline và hỗ trợ phục hồi dữ liệu từ raw snapshot. Phần việc này đứng trước vector indexing, evaluation và observability, nên schema và quy tắc làm sạch phải nhất quán với các module phía sau.

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Crossref ingestion | `src/ingestion/crossref.py`: `parse_crossref_payload()`, `fetch_source_records()`, `load_raw_records()` | Crossref API payload hoặc snapshot cục bộ | `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, danh sách `PaperRecord` | Hoàn thành |
| Cleaning và data modeling | `src/ingestion/cleaning.py`: `build_clean_dataframe()` | Danh sách `PaperRecord`, thời điểm chạy | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Hoàn thành |
| Data contract | Schema `PaperRecord` và clean dataframe | Dữ liệu thô từ Crossref | DOI chuẩn hóa, ngày ISO, `age_days`, `summary_chars`, `text_for_embedding` | Hoàn thành |
| Raw snapshot và recovery | `data/raw/`, phối hợp với `src/pipelines/corruption_flow.py` | Immutable raw snapshot | `papers_clean_repaired.csv/json` và dữ liệu sạch để re-index | Hoàn thành, phối hợp với Đinh Văn Hùng |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Thống nhất schema clean và document identity | RAG & Vector Index, Lê Hoàng Thiên Phú | `paper_id` dùng DOI lowercase ổn định; `text_for_embedding` chứa đủ title, authors, date, categories và summary |
| Cung cấp dữ liệu cho quality/freshness | Observability & Evaluation, Hoàng Trung Khải | Clean dataframe có `summary_chars`, `age_days` và các trường bắt buộc để chạy GX/freshness |
| Kiểm tra dữ liệu sau corruption và repair | Pipeline Integrator, Đinh Văn Hùng | Repair đọc lại raw records thay vì vá trực tiếp dữ liệu corrupted; quality và freshness trở lại trạng thái đạt |
| Chuẩn bị báo cáo và bằng chứng | Báo cáo nhóm | Đối chiếu raw, clean, corruption log, repaired artifacts và metrics |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Parse dữ liệu Crossref | `parse_crossref_payload()` | DOI, title, abstract, authors, categories, dates và URL được chuẩn hóa thành `PaperRecord` | Đọc `data/raw/crossref_records.json`; pipeline tải 24 records |
| Xây cơ chế online/offline | `fetch_source_records()` | Có retry khi API lỗi tạm thời và fallback sang snapshot đã lưu | Chạy baseline với snapshot cục bộ vẫn thu được 24 records |
| Làm sạch dữ liệu | `build_clean_dataframe()` | 24 dòng sạch, bỏ record không hợp lệ và DOI trùng | `data/clean/papers_clean.csv`, `papers_clean.json` |
| Tạo trường dẫn xuất | `age_days`, `authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding` | Dataset sẵn sàng cho quality gate và embedding | Kiểm tra schema trong `papers_clean.json` |
| Hỗ trợ repair idempotent | Raw snapshot và repaired dataset | 24 dòng repaired được dựng lại từ raw records | `data/clean/papers_clean_repaired.json`; repaired quality report đạt |
| Đối chiếu phục hồi | `data/reports/corruption_report.md` | Retrieval hit rate và token F1 trở lại đúng baseline | Baseline/corrupted/repaired metrics |

Một output cụ thể của phần việc là `data/clean/papers_clean.json`. File chứa 24 bài báo với document ID ổn định, ngày ISO, tuổi dữ liệu và nội dung embedding có cấu trúc. Dataset này là input chung cho MiniLM, ChromaDB, benchmark và quality gate.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Dữ liệu Crossref không phải lúc nào cũng đồng nhất. Title có thể là list, abstract chứa thẻ JATS/XML, author hoặc subject có thể thiếu, ngày có nhiều cấu trúc và API có thể lỗi 429 hoặc mất kết nối. Nếu đưa thẳng payload vào embedding, pipeline dễ tạo document ID không ổn định, text nhiễu hoặc record thiếu thông tin quan trọng.

Phần tôi phụ trách giải quyết ba vấn đề:

1. Chuyển payload nguồn thành schema thống nhất và có thể lưu lại.
2. Tạo clean dataframe đủ contract cho retrieval, evaluation và observability.
3. Giữ raw snapshot bất biến để có thể tái hiện hoặc repair dữ liệu.

### Cách triển khai

#### Parse và chuẩn hóa Crossref

- DOI được loại bỏ prefix URL nếu có, chuẩn hóa whitespace và chuyển lowercase.
- Title lấy phần tử hợp lệ đầu tiên rồi chuẩn hóa khoảng trắng.
- Abstract được unescape HTML, loại bỏ JATS/XML tags và chuẩn hóa whitespace.
- Author được ghép từ given name và family name; giá trị trùng bị loại bỏ nhưng vẫn giữ thứ tự.
- Subject được chuyển thành danh sách categories; category đầu tiên dùng làm `primary_category`.
- Ngày được lấy từ các trường Crossref phù hợp và chuyển về ISO `YYYY-MM-DD`.
- Record thiếu DOI, title hoặc published hợp lệ không được đưa vào clean dataset.

#### Fetch, retry và fallback

Request Crossref dùng timeout và retry cho lỗi tạm thời như 429/503. Nếu request không thành công, pipeline ưu tiên đọc `data/raw/crossref_response.json` đã lưu. Sau khi parse, danh sách records được ghi vào `data/raw/crossref_records.json` để các lần chạy sau không phụ thuộc hoàn toàn vào API sống.

#### Cleaning và data modeling

`build_clean_dataframe()` parse ngày bằng UTC, loại record không đáp ứng data contract, khử trùng lặp theo `paper_id`, tính tuổi dữ liệu và tạo nội dung embedding:

```text
Title: <title>
Authors: <authors_joined>
Published: <published>
Categories: <categories_joined hoặc Not provided by Crossref>
Summary: <summary>
```

Tuổi dữ liệu được tính theo ngày:

```python
age_days = (run_date.normalize() - published.normalize()).days
```

Dataframe cuối cùng được sắp xếp theo `published` giảm dần rồi theo `paper_id`, giúp kết quả ổn định giữa các lần chạy.

#### Repair từ raw snapshot

Repair không sửa từng ô trên corrupted dataframe vì cách đó dễ bỏ sót lỗi và khó chứng minh nguồn gốc. Pipeline đọc lại `data/raw/crossref_records.json`, chạy lại cùng cleaning contract, lưu repaired dataset, sau đó re-index và re-evaluate. Đây là repair idempotent: chạy lại từ cùng snapshot và cùng thời điểm tham chiếu sẽ cho cùng dữ liệu sạch.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref REST payload hoặc `data/raw/crossref_response.json`; raw records; `run_date` UTC |
| Raw schema | `paper_id`, `title`, `summary`, `authors`, `categories`, `primary_category`, dates, URLs và comment |
| Output clean | DataFrame 16 cột, gồm schema nguồn và các trường dẫn xuất |
| Document identity | DOI đã chuẩn hóa lowercase trong `paper_id` |
| Module phụ thuộc | `core.config`, `core.utils`, `requests`, `pandas` |
| Module sử dụng output | `retrieval/index.py`, `evaluation/testset.py`, `observability/quality.py`, các pipeline |
| Điều kiện lỗi cần xử lý | API 429/503, mất mạng, payload thiếu trường, ngày parse lỗi, abstract chứa XML, DOI trùng |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã nạp {len(r)} bài báo')"

python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"

python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** ingestion và cleaning tạo 24 records; repair dựng lại 24 records sạch từ raw snapshot.
- **Kết quả thực tế:** baseline có 24 dòng, repaired có 24 dòng; repaired quality và freshness đều đạt.
- **Artifact/log:** `data/raw/`, `data/clean/papers_clean.json`, `data/clean/papers_clean_repaired.json`, `data/quality/repaired_quality_report.json`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Sau khi tiêm nhiều loại lỗi, cần chọn cách phục hồi dữ liệu đủ an toàn và có thể giải thích.
- **Các phương án đã cân nhắc:**
  1. Tìm từng dòng lỗi trong corrupted dataframe rồi sửa lại các field.
  2. Khôi phục từ raw snapshot bất biến, chạy lại toàn bộ cleaning contract rồi re-index.
- **Phương án đã chọn:** Rebuild từ `data/raw/crossref_records.json`.
- **Lý do:** Raw snapshot giữ lineage rõ ràng, tránh phải biết trước mọi dạng corruption và giảm nguy cơ sót lỗi. Cách này có chi phí chạy lại cleaning/index nhưng phù hợp với dataset nhỏ và tăng tính tái lập.
- **Bằng chứng quyết định phù hợp:** Repaired quality chuyển từ fail về pass, freshness chuyển từ stale về fresh, retrieval hit rate phục hồi từ 0.0 lên 1.0 và token F1 phục hồi từ 0.4 lên 0.7158.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `error: externally-managed-environment` khi chạy pip trên Python do Homebrew quản lý. Sau khi tạo môi trường bằng Python 3.14.7, project tiếp tục báo: `requires a different Python: 3.14.7 not in '<3.14,>=3.11'`.
- **Lệnh hoặc bước tái hiện:** `python3 -m pip install --upgrade pip`, sau đó `python -m pip install -e .` trong môi trường dùng Python 3.14.7.
- **Nguyên nhân gốc:** PEP 668 chặn việc sửa môi trường Python hệ thống của Homebrew; đồng thời `pyproject.toml` chỉ hỗ trợ Python từ 3.11 đến dưới 3.14.
- **Cách xử lý:** Tạo `.venv` riêng bằng phiên bản Python tương thích, kích hoạt môi trường rồi cài project editable trong `.venv`. Không dùng `--break-system-packages`.
- **Cách xác minh sau khi sửa:** Các lệnh ingestion, cleaning, baseline và corruption flow chạy bằng Python trong `.venv`, sinh đủ artifacts.
- **Điều học được:** Cần kiểm tra đồng thời quyền quản lý môi trường và version constraint của project. Virtual environment bảo vệ Python hệ thống nhưng vẫn phải dùng đúng phiên bản mà project hỗ trợ.

## 7. Hiểu biết về luồng end-to-end

1. **Từ Crossref đến vector index:** Pipeline gọi Crossref hoặc đọc snapshot, parse thành `PaperRecord`, làm sạch thành dataframe có DOI ổn định và `text_for_embedding`. Quality gate kiểm tra dữ liệu trước khi MiniLM tạo embedding và ChromaDB lưu collection.
2. **Evaluation set và ground truth:** Mỗi câu hỏi chứa một hoặc hai `ground_truth_doc_ids`. Retrieval thành công khi top-k chứa document ID cần tìm. Câu trả lời được so sánh với `ground_truth` bằng token F1 và LLM Judge.
3. **Quality và freshness:** Quality kiểm tra cấu trúc và nội dung như row count, null, uniqueness, summary length. Freshness dùng `age_days` để đo mức độ cũ theo SLA 180 ngày và giới hạn stale ratio 25%.
4. **Dùng cùng test set:** Giữ cố định câu hỏi và ground truth giúp chênh lệch metric phản ánh thay đổi dữ liệu/index, không phải thay đổi độ khó của benchmark.
5. **Xác minh repair:** Repair thành công khi repaired dataset truy vết về raw snapshot, quality và freshness pass lại, đồng thời retrieval/answer metrics phục hồi gần hoặc bằng baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0 | 0.0 | 1.0 | Corruption làm mất toàn bộ lượt hit; rebuild từ raw snapshot phục hồi hoàn toàn |
| `mean_token_f1` | 0.7158 | 0.4000 | 0.7158 | Chất lượng answer giảm 0.3158 rồi trở lại đúng baseline |
| `judge_accuracy` | 0.6 | 0.4 | 0.6 | Phục hồi về snapshot baseline, nhưng metric phụ thuộc LLM Judge |
| `mean_judge_score` | 3.8 | 2.6 | 3.6 | Phục hồi phần lớn nhưng thấp hơn baseline 0.2 điểm |
| Quality checks | Pass | Fail | Pass | Corrupted data vi phạm uniqueness và summary length |
| Freshness status | Fresh | Stale | Fresh | Stale ratio thay đổi 4.17% → 33.33% → 4.17% |

### Kết luận từ số liệu

1. Xóa record mới, làm cũ ngày, tạo DOI trùng và làm rỗng summary → quality/freshness chuyển sang fail → retrieval hit rate giảm từ 1.0 xuống 0.0 và token F1 giảm từ 0.7158 xuống 0.4.
2. Đọc lại raw snapshot, chạy lại cleaning, re-index và dùng lại test set → quality/freshness trở lại pass → retrieval hit rate và token F1 phục hồi đúng baseline.

Corruption ảnh hưởng rõ nhất là **drop latest records kết hợp duplicate rows**. Các câu hỏi benchmark tham chiếu DOI cố định; khi tài liệu đích bị bỏ khỏi corpus, retrieval không thể hit. Việc thêm duplicate giúp row count vẫn là 24, nhưng không thể thay thế coverage đã mất và còn làm giảm độ đa dạng top-k.

Kết quả khác kỳ vọng là mean judge score repaired đạt 3.6 thay vì đúng 3.8. Dataset và retrieval metrics đã phục hồi, nên chênh lệch này phù hợp với giới hạn của LLM Judge không hoàn toàn xác định. Báo cáo nhóm cũng ghi nhận `judge_accuracy` có thể khác giữa các snapshot gọi model.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw snapshot không chỉ là cache offline; nó là mốc lineage giúp tái hiện và phục hồi pipeline.
2. Row count riêng lẻ không đủ đánh giá chất lượng. Dataset corrupted vẫn có 24 dòng nhưng uniqueness, summary validity và freshness đều có thể fail.
3. Chất lượng dữ liệu tác động trực tiếp đến RAG. Mất document identity hoặc nội dung quan trọng có thể làm retrieval hit rate giảm mạnh dù pipeline không phát sinh exception.

### Nếu có thêm thời gian

Tôi sẽ bổ sung manifest cho raw snapshot gồm SHA-256, timestamp tải, query, filter, HTTP status và schema version. Manifest này giúp chứng minh baseline/repaired dùng đúng cùng nguồn raw và phát hiện khi snapshot bị thay đổi ngoài ý muốn. Cách đo cải thiện là chạy repair nhiều lần, kiểm tra hash repaired dataset giống nhau và xác minh metrics không thay đổi khi input snapshot không đổi.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thanh Phong  
**MSSV:** 2A202602843  
**Ngày xác nhận:** 2026-09-25
