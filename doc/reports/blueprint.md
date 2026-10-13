# Blueprint CI/CD cho RAG và guardrails

Nhóm: {{Tên nhóm}}

Người phụ trách: {{Họ tên và MSSV}}

Đây là **đề xuất CI/CD**, không phải workflow đã được triển khai/chạy.
Nguồn kết quả: artifacts/ragas_50q.json, judge_results.json, guard_results.json.
Run timestamp: {{created_at}} (Phase C: 2026-10-13T03:51:54Z); guard models: gemini-3.5-flash-lite (NeMo 0.10.0 self check input/output).
Models generation/evaluator/judge từ A/B: {{models theo từng vai trò và nguồn report}}.

## Kiến trúc và failure action

Input → Presidio → NeMo input → RAG → NeMo output → response.
Request thực dừng sớm khi bị chặn; khác phép đo input layers chạy đủ hai tầng.

{{Mô tả data flow, failure action, log/redact, nơi giữ secrets và điều kiện fallback.}}

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
{{Đề xuất lệnh job và cách script trả nonzero khi không đạt. MIN_* là biến đề
xuất, không tự làm quality gate nếu runner chưa kiểm tra ngưỡng. Ghi rõ workflow
chưa triển khai, hoặc dẫn bằng chứng nếu nhóm thực sự đã triển khai.}}

## Monitoring và cải tiến

{{Nêu metric, ngưỡng cảnh báo, cách lấy samples, xử lý false positives, drift,
privacy và người xử lý. Dùng kết quả thật và ghi giới hạn của bộ 50/20/8/4.}}

RAGAS mean/worst distribution: {{giá trị}}.
Cohen’s κ: {{giá trị}}.
Attacks passed: 20/20 (presidio 4, nemo_input 16); clean false_positive_rate: 0.0 (8/8 allowed); output cases 4/4 đúng.
{{Nêu 3–5 câu cải tiến có thể kiểm tra, gắn với bằng chứng của nhóm.}}
