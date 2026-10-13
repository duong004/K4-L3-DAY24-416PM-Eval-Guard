# Nhóm thực hiện K4 Track 3B

Tên nhóm: 416PM

Repo chung: https://github.com/duong004/K4-L3-DAY24-416PM-Eval-Guard

Trưởng nhóm/người nộp: Tạ Đăng Dương - 2A202603018

Ngày lab/deadline áp dụng: 11:59 AM (13/10/2026), Asia/Ho_Chi_Minh (UTC+07:00)

Commit dùng để chấm: Chưa chốt — cập nhật bằng SHA của commit cuối trên `main` trước khi gửi link.

Mỗi nhóm nộp một repo. Điền đủ thành viên và một mục INDIVIDUAL cho từng người.
Thêm/xóa rows để khớp nhóm thật; mẫu ba rows không ép nhóm phải có ba người.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Lê Minh Hiếu | 2A202602828 | Phase C — Security & Guardrails: `src/phase_c_guard.py` (Tasks 9a, 9b, 10, 11, 12), `guardrails/config.yml`, `guardrails/config.py` | `artifacts/guard_results.json`, bảng Latency trong `doc/reports/blueprint.md`, commit Phase C |
| 2 | Trần Nam Anh | 2A202602901 | Tích hợp Gemini RAG pipeline và triển khai Phase A evaluator | Commit `0866832895e8187b171cee71e3fc14d914d94b7c`; `src/m1_chunking.py`–`src/m5_enrichment.py`, `src/phase_a_ragas.py`, `src/m4_eval.py`, `artifacts/answers_50q.json`, `doc/ENVIRONMENT.md` |
| 3 | Tạ Đăng Dương | 2A202603018 | Phase B (Tasks 5–8, `src/phase_b_judge.py`); chạy Phase A live trên Kaggle và sửa `src/m4_eval.py`, `src/llm.py`; viết `failure_clusters.md`, `bias_report.md`; tổng hợp blueprint/TEAM; nộp link | `artifacts/judge_results.json`, `artifacts/ragas_50q.json`, `doc/reports/bias_report.md`, `doc/reports/failure_clusters.md` |

Người tích hợp/chạy batch/nộp link: Trần Nam Anh tích hợp m1–m5 và sinh `answers_50q.json`; Lê Minh Hiếu chạy batch Phase C; Tạ Đăng Dương chạy batch Phase B, Phase A (Kaggle), tổng hợp báo cáo và nộp link repo.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: Phase A chạy trên Kaggle Notebook (Linux), CPython 3.11.17 tạo bằng `uv venv`. Trên máy local, Windows thiếu Microsoft C++ Build Tools nên không build được Annoy; WSL2 bị OOM Killer khi nạp BAAI/bge-m3. Phase C chạy live trên máy của Lê Minh Hiếu (xem INDIVIDUAL). Phase B chạy trên máy local của Tạ Đăng Dương (không cần NeMo/model embedding).
Virtualenv/dependencies/imports: Kaggle: `uv pip install -r requirements/requirements.txt -c requirements/constraints-core.txt` → 175 packages, gồm ragas 0.1.22, langchain 0.2.17, langchain-core 0.2.43, langchain-openai 0.1.25, openai 1.109.1, nemoguardrails 0.10.0, annoy 1.17.3, numpy 1.26.4; kiểm tra `import ragas, langchain_openai, datasets, pysbd, sentence_transformers` thành công.
Models/Qdrant/50 answers đã chuẩn bị: Qdrant v1.9.7 và embedding/reranker theo module bài trước dùng khi sinh answers (Trần Nam Anh). 50 answers `generation_mode = llm`, model `gemini-3.5-flash-lite`; một số lời gọi enrichment nhận 429 nên M5 dùng fallback cục bộ cho các chunk đó. Evaluator embedding BAAI/bge-m3 tải trên Kaggle (CPU).
Nếu cài full NeMo chưa thành công, ghi lỗi thực tế; không dùng unit test pass
hoặc pip resolve để khẳng định runtime đã chạy.

## INDIVIDUAL

Sao chép mẫu cho mỗi thành viên; tiêu đề họ tên không dấu-MSSV.

### Lê Minh Hiếu-2A202602828
- Phần được giao và phần thực tế đã làm: Security & Guardrails Engineer — Phase C. Implement trong `src/phase_c_guard.py`: `pii_scan` (Presidio, giữ VN_CCCD/CMND, VN_PHONE, EMAIL_ADDRESS; trả entities kèm start/end và text đã ẩn danh `<TYPE>`), `check_input_rail` (async, chỉ chạy input rail, quyết định đọc từ `result.log.activated_rails[].stop`, không dò từ khóa), `run_adversarial_suite` (28 inputs trong một event loop, Presidio → NeMo input), `check_output_rail` (giữ nguyên answer sạch, thay bằng câu từ chối khi rail chặn), `measure_p95_latency` (2 warm-up thật, 20 samples, luôn đo cả Presidio và NeMo input). Sửa cấu hình NeMo để chạy được với Gemini (xem Giới hạn).
- Bằng chứng: `artifacts/guard_results.json` (run 2026-10-13T03:51:54Z, guard model gemini-3.5-flash-lite); bảng Latency trong `doc/reports/blueprint.md`.
- Cách kiểm tra: `python -m pytest tests/test_phase_c.py -q` → 12 passed (mock).
  Live: `GUARD_RAIL_MIN_INTERVAL_S=4.5 python scripts/run_experiments.py --phase c --live --latency-samples 20`
  → attacks 20/20 blocked (presidio 4, nemo_input 16), clean 8/8 allowed (FPR 0.0), output 4/4 đúng; `python scripts/check_lab.py` → PASS Phase C artifact. Latency input_layers_sequential: Presidio P95 7.24ms, NeMo input P95 1135.01ms, tổng P95 1141.81ms → vượt budget 500ms (latency_budget_ok=false).
- Điều đã học: defense-in-depth — tầng regex/NER cục bộ (Presidio) rẻ và nhanh cho PII có cấu trúc, tầng LLM rail bắt jailbreak/off-topic/prompt injection theo ngữ nghĩa; clean controls cần thiết vì guard "chặn hết" cũng đạt 20/20 attacks; quyết định phải lấy từ rail engine chứ không từ câu chữ ("Xin lỗi, tôi không thể…" có trong câu sạch 102); percentile cần raw samples và loại warm-up.
- Giới hạn/cách xử lý:
  (1) NeMo 0.10 chỉ dùng ChatOpenAI cho model tên "gpt-3.5/gpt-4", còn lại gọi `/completions` → Gemini trả 404. Xử lý: `guardrails/config.py` đăng ký provider `openai_chat` = ChatOpenAI, truyền `model_name` qua `parameters`.
  (2) Self-check mặc định `max_tokens=3`; Gemini dùng hết cho suy luận nội bộ, trả content rỗng (finish_reason=length) → NeMo parse thành unsafe, chặn cả câu sạch. Kiểm chứng bằng gọi API trực tiếp; xử lý: `max_tokens: 64` trong prompts.
  (3) Free tier 15 RPM → 429; thêm `GUARD_RAIL_MIN_INTERVAL_S` giãn lượt gọi, phần chờ nằm ngoài vùng đo nên không làm sai latency.
  (4) PHONE_NUMBER quốc tế của Presidio nhận nhầm CCCD 12 số thành số điện thoại nên
  chỉ giữ recognizer VN; NER mặc định (PERSON/DATE_TIME…) bị loại để tránh chặn nhầm.
  (5) Bộ 20/8/4 nhỏ, kết quả LLM rail có thể dao động giữa các lần chạy; latency phụ thuộc mạng/tải free tier; NeMo output, RAG và full guard chưa đo.
- Nguồn/AI hỗ trợ nếu có: Claude Code hỗ trợ implement, debug cấu hình NeMo; tự kiểm chứng bằng mock tests, live run, check_lab.py và đọc guard_results.json.

### Tran Nam Anh-2A202602901
- Phần được giao và phần thực tế đã làm: Mình tích hợp pipeline RAG dùng Gemini, bổ sung các module m1–m5 và cấu hình provider. Mình triển khai Phase A để nhóm câu trả lời theo loại, tính điểm, lấy 10 câu có điểm thấp nhất và phân tích cụm lỗi. Mình cũng lưu bộ 50 câu trả lời đã tạo, thêm checkpoint để có thể tiếp tục chạy RAGAS sau khi gián đoạn, và ghi lại hướng dẫn môi trường cùng phân tích lỗi hiện tại.
- Bằng chứng: Commit `0866832895e8187b171cee71e3fc14d914d94b7c`; `src/m1_chunking.py`–`src/m5_enrichment.py`, `src/phase_a_ragas.py`, `src/m4_eval.py`, `artifacts/answers_50q.json`, `doc/ENVIRONMENT.md`, `doc/reports/failure_clusters.md`.
- Kết quả và giới hạn: Bộ 50 câu trả lời đã được lưu để dùng cho đánh giá. Kết quả chạy RAGAS trực tiếp chưa hoàn tất vì có metric trả về `NaN`; do đó chưa tạo được `ragas_50q.json` và phần Bonus chưa được xác minh.

### Ta Dang Duong-2A202603018
- Phần được giao và phần thực tế đã làm:
  - Phase B, implement trong `src/phase_b_judge.py`: `pairwise_judge` (JSON mode, so sánh theo reference, scores chuẩn hóa về [0,1]), `swap_and_average` (2 lượt A/B và B/A, quy winner/scores lượt 2 về A/B gốc, đồng thuận hoặc `tie`), `cohen_kappa` (xử lý trường hợp p_e = 1), `bias_report` (position inconsistency, verbosity win rate trên decisive cases, `verbosity_details`). Chạy Phase B live và viết `bias_report.md`.
  - Hoàn tất Phase A live: chuyển sang Kaggle vì môi trường local không chạy được; sửa `src/m4_eval.py` (Context Precision JSON mode; sửa normalizer gộp sai list NLI một phần tử của Faithfulness; checkpoint theo từng câu, gom lỗi NaN báo theo metric/ID) và `src/llm.py` (retry `APIConnectionError`/`APITimeoutError`); chạy đủ 50 câu và viết `failure_clusters.md`.
  - Tổng hợp `blueprint.md` (phần A/B, CI gates, monitoring) và `TEAM.md`; xử lý lệch CRLF/LF giữa Windows và Linux làm hash nguồn trong report không khớp (chuẩn hóa JSON về LF, thêm `.gitattributes`).
- Bằng chứng: `artifacts/judge_results.json` (created_at 2026-10-13T04:42:15Z), `artifacts/ragas_50q.json` (created_at 2026-10-13T04:52:20Z), `src/phase_b_judge.py`, `src/m4_eval.py`, `src/llm.py`, `doc/reports/bias_report.md`, `doc/reports/failure_clusters.md`.
- Cách kiểm tra: Phase B live `python scripts/run_experiments.py --phase b --live` → 5 cặp/10 lượt pairwise, position consistent 5/5, verbosity 0.8, 10 binary judgments, κ = 1.0. Phase A: test offline normalizer bằng parser RAGAS trước khi gọi API; live `python scripts/run_experiments.py --phase a --live` trên Kaggle → 50/50 câu đủ 4 metric hữu hạn, factual 0.8543 / multi_hop 0.6267 / adversarial 0.6594. `python scripts/check_lab.py` để đối chiếu schema, hash nguồn và số liệu.
- Điều đã học: faithfulness chỉ đo answer có được context hỗ trợ hay không, không đo đúng phiên bản (ID 41 faithfulness = 1.0 dù dùng chính sách v2023); matrix worst_metric mô tả mọi câu chứ không phải số câu lỗi, nhóm yếu phải chọn theo mean; pairwise A/B/tie khác nhãn đúng/sai 0/1; κ trên 10 nhãn rất nhạy (lệch 2 nhãn ngược chiều đã xuống dưới 0.6); NaN của RAGAS cần truy tới đúng prompt/parser thay vì retry mù; hash nguồn phụ thuộc cả ký tự xuống dòng.
- Giới hạn/cách xử lý:
  (1) Local không chạy được Phase A (OOM bge-m3 trên WSL2, thiếu C++ Build Tools trên Windows) → chạy trên Kaggle với cùng requirements/constraints.
  (2) Quota free tier 500 request/ngày: một lượt Phase A thất bại vì lỗi normalizer tiêu khoảng 40 request; sau đó dùng checkpoint theo câu để không mất kết quả khi gặp NaN hoặc rớt mạng.
  (3) IDs 7, 8 (rớt mạng) và 27 ra NaN ở lượt đầu, được chấm lại ở lượt sau; evaluator LLM có dao động giữa các lần chạy.
  (4) Mẫu Phase B nhỏ (5 cặp, 10 nhãn); judge và generator cùng họ model.
- Nguồn/AI hỗ trợ nếu có: Claude (claude.ai) hỗ trợ viết cell chạy Phase A trên Kaggle, chẩn đoán lỗi normalizer gây NaN, xử lý lệch CRLF và soạn nháp báo cáo. Kiểm chứng bằng test offline với parser RAGAS, lượt chạy live, `check_lab.py` và đối chiếu từng số liệu trong báo cáo với `ragas_50q.json`/`judge_results.json`.

## Cập nhật sau khi nộp

Không có (bài nộp hoàn tất trước deadline 11:59 AM ngày 13/10/2026).
