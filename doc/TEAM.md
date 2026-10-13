# Nhóm thực hiện K4 Track 3B

Tên nhóm: {{Tên nhóm}}

Repo chung: {{Link repo}}

Trưởng nhóm/người nộp: {{Họ tên và MSSV}}

Ngày lab/deadline áp dụng: {{Ngày giờ theo thông báo lớp}} — Asia/Ho_Chi_Minh (UTC+07:00)

Commit dùng để chấm: {{Commit SHA}}

Mỗi nhóm nộp một repo. Điền đủ thành viên và một mục INDIVIDUAL cho từng người.
Thêm/xóa rows để khớp nhóm thật; mẫu ba rows không ép nhóm phải có ba người.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Lê Minh Hiếu | 2A202602828 | Phase C — Security & Guardrails: `src/phase_c_guard.py` (Tasks 9a, 9b, 10, 11, 12), `guardrails/config.yml`, `guardrails/config.py` | `artifacts/guard_results.json`, bảng Latency trong `doc/reports/blueprint.md`, commit Phase C |
| 2 | Trần Nam Anh | 2A202602901 | Tích hợp Gemini RAG pipeline và triển khai Phase A evaluator | Commit `0866832895e8187b171cee71e3fc14d914d94b7c`; `src/m1_chunking.py`–`src/m5_enrichment.py`, `src/phase_a_ragas.py`, `src/m4_eval.py`, `artifacts/answers_50q.json`, `doc/ENVIRONMENT.md`, `doc/reports/failure_clusters.md` |
| 3 | {{Họ tên}} | {{MSSV}} | {{Phase/file/hàm}} | {{Commit/PR/report}} |

Người tích hợp/chạy batch/nộp link: {{Họ tên, công việc và bằng chứng}}.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: {{Phiên bản thực tế}}.
Virtualenv/dependencies/imports: {{Lệnh và kết quả}}.
Models/Qdrant/50 answers đã chuẩn bị: {{Bằng chứng và giới hạn/fallback}}.
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

## Cập nhật sau khi nộp

{{Ghi phiên bản nộp; nếu sửa sau deadline, ghi commit/thời điểm/lý do và thông báo
coach cho phép áp dụng bản cập nhật. Nếu không có cập nhật, ghi rõ không có.}}
