# Blueprint CI/CD cho RAG và guardrails

Nhóm: 416PM

Người phụ trách: Lê Minh Hiếu - 2A202602828 (guardrails, latency); Tạ Đăng Dương - 2A202603018 (tổng hợp A/B, CI gates, monitoring); Trần Nam Anh - 2A202602901 (pipeline RAG)

Đây là **đề xuất CI/CD**, không phải workflow đã được triển khai/chạy.
Nguồn kết quả: artifacts/ragas_50q.json, judge_results.json, guard_results.json.
Run timestamp: Phase A 2026-10-13T04:52:20Z; Phase B 2026-10-13T04:42:15Z (Phase C: 2026-10-13T03:51:54Z); guard models: gemini-3.5-flash-lite (NeMo 0.10.0 self check input/output).
Models generation/evaluator/judge từ A/B: generation `gemini-3.5-flash-lite` (answers_50q.json, metadata A/B); evaluator `gemini-3.5-flash-lite` + `BAAI/bge-m3` (ragas_50q.json); judge `gemini-3.5-flash-lite` (judge_results.json).

## Kiến trúc và failure action

Input → Presidio → NeMo input → RAG → NeMo output → response.
Request thực dừng sớm khi bị chặn; khác phép đo input layers chạy đủ hai tầng.

Data flow và failure action đề xuất:

| Tầng | Kiểm tra | Khi phát hiện vấn đề | Bằng chứng hiện có |
|---|---|---|---|
| Presidio (local) | CCCD/CMND, SĐT VN, email (recognizer VN; bỏ PHONE_NUMBER quốc tế và NER mặc định để tránh chặn nhầm) | Chặn input, trả câu từ chối; chỉ log bản đã ẩn danh `<TYPE>` | 4/20 attacks bị chặn ở tầng này |
| NeMo input rail | Self check input (jailbreak, prompt injection, off-topic) | Trả câu từ chối định nghĩa trong `rails.co`, không gọi RAG; quyết định đọc từ `activated_rails`, không dò từ khóa | 16/20 attacks bị chặn; 8/8 câu sạch được cho qua |
| RAG (m1–m5) | Hybrid search + rerank, top_k = 3 | Không có context hoặc generation lỗi → extractive fallback, ghi `generation_mode` | 50/50 answers `generation_mode = llm` |
| NeMo output rail | Self check output | Thay answer bằng câu từ chối/redact; answer sạch giữ nguyên | 4/4 output cases đúng |

Fallback khi dịch vụ guard lỗi (đề xuất, chưa triển khai): input rail fail-closed. Nếu NeMo/Gemini
trả 429 hoặc timeout sau retry thì từ chối request và báo thử lại; Presidio vẫn chạy cục bộ. Log chỉ
chứa text đã ẩn danh, request id, rail kích hoạt và latency, không chứa prompt gốc có PII.

Secrets: `GEMINI_API_KEY` chỉ nằm trong `.env` (bị ignore) hoặc secret store của CI/notebook; không
in ra log hay commit. `.env.example` chỉ chứa tên biến.

## Phạm vi và số đo latency

Bắt buộc Task 12: **input_layers_sequential**, Presidio + NeMo input, không
short-circuit. Engines tạo trước đo; có hai warm-up thật không tính vào mẫu.
Percentile nội suy tuyến tính từ raw samples; tổng từ tổng từng sample.

Số mẫu timed: 20; warm-up: 2;
phương pháp: linear (vị trí (n−1)×q trên raw samples trong artifacts/guard_results.json).

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---|---|---|---|
| Presidio | 6.24 | 7.24 | 8.33 | Đã đo (Task 12); local regex + spaCy, không gọi mạng |
| NeMo input | 736.99 | 1135.01 | 1153.19 | Đã đo (Task 12); 1 lượt gọi Gemini self check input |
| Input guard sequential | 742.77 | 1141.81 | 1159.53 | Đã đo (Task 12); vượt target 500ms |
| RAG | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| NeMo output | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| Full guard / short-circuit request | chưa đo | chưa đo | chưa đo | Không suy từ input_guard_ms |

Input-layer budget target: 500ms; kết quả thực tế: input_guard_ms P95 = 1141.81ms,
latency_budget_ok = false.

Bottleneck là NeMo input (~99% thời gian mỗi sample): mỗi lượt là một round-trip HTTP
tới Google AI Studio (free tier), phụ thuộc mạng và tải phía nhà cung cấp; 20 samples
nằm trong khoảng 622–1158ms. Presidio chỉ ~6–8ms. Hướng giảm: chạy Presidio và NeMo
song song (asyncio.gather) với request thật vì Presidio không cần chờ, dùng model
guard nhỏ/self-hosted gần app, cache quyết định cho câu hỏi lặp lại, hoặc lọc trước
bằng classifier cục bộ và chỉ gọi LLM rail cho câu không chắc chắn.

Lưu ý phép đo: các lượt gọi rail được giãn ≥4.5s (GUARD_RAIL_MIN_INTERVAL_S) để không
vượt quota 15 RPM; thời gian chờ nằm ngoài vùng perf_counter nên không tính vào sample.
RAG, NeMo output và full guard/short-circuit request chưa đo; kế hoạch: gắn timestamps
perf_counter ở từng tầng của request thật, 2 warm-up, ≥20 mẫu, cùng phương pháp linear.

## CI gates đề xuất

- RAGAS faithfulness ≥0.75, avg_score ≥0.65 trên 50 câu.
- Attacks ≥18/20 cho CI đề xuất; clean 8/8 allowed; output cases đúng.
- Full guard P95 <500ms chỉ áp dụng sau khi thực sự đo full guard.

Mốc bắt buộc lab vẫn attacks ≥15/20; bonus ≥18/20 kèm clean controls đạt.

Workflow **chưa được tạo** trong repo. Thiết kế đề xuất gồm hai job:

1. **Mỗi pull request (offline, không tốn quota):**
   `python -m pytest tests/ -q` rồi `python scripts/check_lab.py`. Job fail khi pytest hoặc checker
   trả mã khác 0 (schema, hash nguồn, counts, percentiles).
2. **Định kỳ/thủ công (live, có chi phí API):**
   `python scripts/run_experiments.py --phase a --live`, `--phase b --live`,
   `--phase c --live --latency-samples 20`, sau đó chạy một script gate (đề xuất `scripts/ci_gates.py`,
   **chưa tồn tại**) đọc ba JSON và `sys.exit(1)` nếu dưới ngưỡng. Các biến `MIN_FAITHFULNESS = 0.75`,
   `MIN_AVG_SCORE = 0.65`, `MIN_KAPPA = 0.6`, `MIN_ATTACKS_BLOCKED = 18`, `MAX_CLEAN_FP = 0` chỉ có tác
   dụng khi script này thực sự kiểm tra; runner hiện tại không tự làm gate.

Đối chiếu với kết quả đo hiện tại:

| Gate đề xuất | Giá trị đo | Trạng thái |
|---|---|---|
| Faithfulness toàn bộ ≥0.75 | 0.8275 | Đạt |
| avg_score toàn bộ ≥0.65 | 0.7243 | Đạt |
| avg_score từng distribution ≥0.65 (nếu áp theo nhóm) | multi_hop 0.6267 | Không đạt |
| κ ≥0.6 | 1.0 | Đạt (10 nhãn) |
| Attacks ≥18/20, clean 8/8, output 4/4 | 20/20, 8/8, 4/4 | Đạt |
| Input guard P95 <500ms | 1141.81ms | Không đạt; để ở mức cảnh báo cho đến khi tối ưu |

## Monitoring và cải tiến

Metric đề xuất (chưa triển khai):

| Metric | Cách lấy | Ngưỡng cảnh báo đề xuất |
|---|---|---|
| Block rate theo tầng (Presidio / NeMo input / NeMo output) | Đếm từ log quyết định rail mỗi request | Thay đổi >2× so với trung bình 7 ngày |
| False positive | Lấy mẫu câu bị chặn + phản hồi người dùng, duyệt thủ công hằng tuần | Bất kỳ câu sạch nào thuộc nhóm nghỉ phép/lương/VPN/mật khẩu bị chặn |
| Input guard P95, tỷ lệ 429/timeout của NeMo | perf_counter quanh từng tầng, ≥20 mẫu/cửa sổ | P95 >1200ms hoặc 429 >5% |
| Tỷ lệ từ chối "Không tìm thấy." | Đếm answer từ chối trên traffic | >10% (Phase A đo 5/50 = 10%, 4/5 có context liên quan) |
| RAGAS + binary judge trên mẫu có nhãn | Chạy hằng tuần trên mẫu cố định + mẫu mới có nhãn | faithfulness <0.75 hoặc multi_hop avg <0.60 |
| Drift phiên bản chính sách | Phát hiện answer trích tài liệu có "ĐÃ THAY THẾ" | Bất kỳ trường hợp nào |

Privacy: log chỉ lưu text đã ẩn danh; mẫu duyệt thủ công không chứa PII thật. Người xử lý: phần guard
(Lê Minh Hiếu), phần RAG/retrieval (Trần Nam Anh), phần eval/judge (Tạ Đăng Dương).
Giới hạn: bộ 50/20/8/4 nhỏ; adversarial chỉ 10 câu, calibration 10 nhãn, 5 cặp pairwise; kết quả
LLM rail và evaluator có thể dao động giữa các lần chạy.

RAGAS mean/worst distribution: avg_score toàn bộ 0.7243; nhóm yếu nhất multi_hop 0.6267 (context_precision 0.3417); factual 0.8543, adversarial 0.6594.
Cohen’s κ: 1.0 trên 10 supplied model_answers (6 nhãn 1, 4 nhãn 0).
Attacks passed: 20/20 (presidio 4, nemo_input 16); clean false_positive_rate: 0.0 (8/8 allowed); output cases 4/4 đúng.

Cải tiến có thể kiểm tra:

1. Sửa prompt generation để trả lời phần có căn cứ thay vì "Không tìm thấy." → kỳ vọng answer_relevancy > 0 ở IDs 2, 21, 22, 23, 33, 46, 48 (hiện đều = 0).
2. Tăng `RERANK_TOP_K` 3→5 hoặc tách câu hỏi nhiều vế → đo lại context_precision/recall của multi_hop (hiện 0.3417 / 0.7083).
3. Retrieval version-aware (hạ hạng tài liệu "ĐÃ THAY THẾ") → binary judge label = 1 cho IDs 41, 42, 44, 49.
4. Chạy Presidio và NeMo input song song, đo lại 20 mẫu → so sánh P95 với 1141.81ms.
5. Thêm binary correctness judge vào eval định kỳ cho adversarial, vì faithfulness = 1.0 ở ID 41 dù answer dùng bản v2023.