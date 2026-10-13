# Phân tích lỗi Phase A

Nguồn: `artifacts/ragas_50q.json` — `run_kind = live`, `created_at = `2026-10-13T04:52:20.602936+00:00``.
Models: generation `gemini-3.5-flash-lite`; evaluator `gemini-3.5-flash-lite` + `BAAI/bge-m3`
(lấy từ `metadata.evaluator_models` do m4 trả về, không suy từ JUDGE_MODEL). RAGAS 0.1.22.

Code Tasks 1–4 và m4 ban đầu: Trần Nam Anh — 2A202602901.   

Chạy lượt live, sửa m4/llm và viếtbáo cáo này: Tạ Đăng Dương — 2A202603018.

## Bằng chứng lần chạy

- Input: `artifacts/answers_50q.json`, 50 câu (factual 20, multi_hop 20, adversarial 10), cả 50 có
  `generation_mode = llm`. Answer không bị thay bằng ground_truth. Theo ghi nhận trước đó của người
  tích hợp, IDs 3, 5, 8, 10 đã được viết lại thành câu hoàn chỉnh từ question/context bằng Gemini;
  ID 19 đã ở dạng một câu hoàn chỉnh khi chạy lượt này.
- Môi trường: Kaggle Notebook, venv CPython 3.11.17 (uv), cài `requirements/requirements.txt` với
  `constraints-core.txt`, chạy `python scripts/run_experiments.py --phase a --live`. Không chạy local
  vì nạp BAAI/bge-m3 bị OOM Killer trên WSL2 và Windows thiếu C++ Build Tools cho Annoy.
- Sửa trước khi có kết quả hợp lệ (không đổi công thức metric, không gán điểm thay cho NaN):
  1. Context Precision dùng `response_format = json_object` để Gemini trả đủ `reason` và `verdict`.
  2. Normalizer JSON của m4 không còn gộp list NLI một phần tử (có key `statement`) của Faithfulness
     thành object. Lỗi này làm mọi answer một câu (ID 1, 3, 5 ở lượt đầu) ra `NaN`. Bản sửa được
     kiểm tra offline bằng chính parser RAGAS trước khi gọi API.
  3. Checkpoint theo từng câu, ghi nguyên tử, chỉ nạp khi hash input/model/RAGAS version khớp; câu
     có metric `NaN` không được lưu và được đánh giá lại.
  4. `src/llm.py` retry thêm cho `APIConnectionError` / `APITimeoutError`.
- `NaN` gặp trong lúc chạy: ID 7 (context_precision) và ID 8 (context_recall) do `APIConnectionError`;
  ID 27 (context_recall) không xác định được nguyên nhân. Cả ba được đánh giá lại ở lượt sau và cho
  giá trị hữu hạn.
- Kết quả: 50/50 câu đủ 4 metric hữu hạn trong [0, 1]; per_distribution 20/20/10.

## Điểm theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) | Toàn bộ (50) |
|---|---:|---:|---:|---:|
| faithfulness | 0.9250 | 0.7854 | 0.7167 | 0.8275 |
| answer_relevancy | 0.8673 | 0.6713 | 0.6808 | 0.7516 |
| context_precision | 0.7917 | **0.3417** | 0.6333 | 0.5800 |
| context_recall | 0.8333 | 0.7083 | 0.6067 | 0.7380 |
| **avg_score** | **0.8543** | **0.6267** | **0.6594** | **0.7243** |

Nhóm yếu nhất theo mean `avg_score` thấp nhất: **multi_hop (0.6267)**, kế đến adversarial (0.6594),
factual (0.8543). Ô thấp nhất cả bảng là context_precision của multi_hop (0.3417).

## Failure matrix `worst_metric × distribution`

| worst_metric | factual | multi_hop | adversarial | Tổng |
|---|---:|---:|---:|---:|
| faithfulness | 1 | 4 | 3 | 8 |
| answer_relevancy | 9 | 3 | 0 | 12 |
| context_precision | 5 | **12** | 4 | **21** |
| context_recall | 5 | 1 | 3 | 9 |
| Tổng cột (= kích thước nhóm) | 20 | 20 | 10 | 50 |

Cách đọc:

- Matrix đếm metric thấp nhất của **mọi** câu, không phải số câu lỗi. Ví dụ ID 1 có avg 0.9994;
  answer_relevancy (0.9978) là "worst" chỉ vì ba metric còn lại xấp xỉ 1. Phần lớn 9 câu factual
  có worst = answer_relevancy thuộc loại này.
- context_precision là worst metric phổ biến nhất (21/50), tập trung ở multi_hop (12/20). 10/20 câu
  multi_hop có CP = 0 (IDs 21, 22, 26, 28, 30, 33, 36, 37, 39, 40).
- Không quy toàn bộ CP thấp cho retrieval: IDs 26, 28, 36 có context_recall = 1.0 (mọi ý của reference
  đều có trong contexts) nhưng CP = 0. Với câu multi-hop, mỗi chunk chỉ chứa một phần đáp án nên
  evaluator chấm từng chunk là "không đủ hữu ích". CP cần đọc cùng CR.

## Bottom 10

Cột `worst_metric` và chẩn đoán tự động lấy nguyên từ output Task 3 trong JSON (exporter giữ nguyên).
Cột "Đọc lại" là phân tích thủ công question/answer/contexts/reference.

| Rank | ID | Distribution | F | AR | CP | CR | avg | worst_metric (Task 3) | Đọc lại |
|---:|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | 21 | multi_hop | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2500 | answer_relevancy — "Answer doesn't match question" | Không có chunk khung lương Senior trong contexts (CR = 0). Answer đúng phần 18 ngày phép nhưng nói "không tìm thấy" phần lương. Gốc là retrieval multi-hop thiếu tài liệu thứ hai. |
| 2 | 2 | factual | 0.0000 | 0.0000 | 0.3333 | 1.0000 | 0.3333 | faithfulness — "LLM hallucinating" | Không phải bịa: context 3 có "200.000.000 VNĐ/năm" (CR = 1). Chunk 1 bị cắt ngay sau "Hạn mức bảo hiểm:", con số nằm ở chunk xếp hạng 3. Generator trả "Không tìm thấy." — từ chối sai. |
| 3 | 22 | multi_hop | 1.0000 | 0.0000 | 0.0000 | 0.3333 | 0.3333 | answer_relevancy — "Answer doesn't match question" | Contexts có yêu cầu xác nhận cấu hình từ phòng CNTT nhưng thiếu bảng thẩm quyền 5–50 triệu. Generator từ chối toàn bộ thay vì trả lời phần có căn cứ. |
| 4 | 33 | multi_hop | 1.0000 | 0.0000 | 0.0000 | 0.5000 | 0.3750 | answer_relevancy — "Answer doesn't match question" | Phần 19 ngày phép đúng. Cả 3 contexts đều về phép năm, không có chunk phụ cấp nên phần phụ cấp bị trả "không tìm thấy". |
| 5 | 46 | adversarial | 0.0000 | 0.0000 | 1.0000 | 0.6667 | 0.4167 | faithfulness — "LLM hallucinating" | Bẫy phủ định bị cắt đôi: "Nhân viên thử việc **KHÔNG được" nằm cuối một chunk khác; chunk được lấy bắt đầu bằng "nghỉ phép năm**." Generator không thấy phủ định nên trả "Không tìm thấy." |
| 6 | 48 | adversarial | 0.0000 | 0.0000 | 1.0000 | 0.7500 | 0.4375 | faithfulness — "LLM hallucinating" | Context 1 nêu rõ thử việc "chưa được hưởng gói bảo hiểm sức khỏe PVI" nhưng answer là "Không tìm thấy." Retrieval đúng; lỗi từ chối ở generation. |
| 7 | 40 | multi_hop | 1.0000 | 0.6867 | 0.0000 | 0.2500 | 0.4842 | context_precision — "Too many irrelevant chunks" | 2/3 contexts là chính sách thử việc, không liên quan cách xử lý sự cố; thiếu chunk "không tự xử lý malware"/hotline nên vế "không nên làm" bỏ trống. |
| 8 | 49 | adversarial | 0.6667 | 0.8813 | 0.0000 | 0.4000 | 0.4870 | context_precision — "Too many irrelevant chunks" | Answer nhận đúng v2024 là bản hiện hành nhưng không nêu 15 ngày và quy tắc thâm niên; context 2 (nghỉ không lương) không liên quan. |
| 9 | 23 | multi_hop | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 0.5000 | faithfulness — "LLM hallucinating" | Contexts đủ dữ kiện (cam kết 1 năm, hoàn trả 100%) nhưng generator không suy luận 8 tháng < 1 năm, trả "Không tìm thấy." |
| 10 | 37 | multi_hop | 1.0000 | 0.6449 | 0.0000 | 0.5000 | 0.5362 | context_precision — "Too many irrelevant chunks" | Nêu đúng hai vi phạm nhưng thiếu yêu cầu báo cáo trong 1 giờ qua helpdesk (chunk đó không được lấy). |

### Các cụm lỗi chính

1. **Từ chối sai ("Không tìm thấy.")** — 5/50 answers là "Không tìm thấy." (IDs 2, 22, 23, 46, 48) và
   cả 5 nằm trong bottom 10. 4/5 có context_recall ≥ 0.6667, tức thông tin phần lớn đã được lấy về.
   Cộng thêm 2 câu từ chối một phần (IDs 21, 33), có đúng 7 câu answer_relevancy = 0 và cả 7 đều ở
   bottom 10. Cây chẩn đoán gán nhãn "LLM hallucinating"/"Answer doesn't match question" cho nhóm này,
   nhưng nguyên nhân thật là generation quá thận trọng, cộng ranh giới chunk (IDs 2, 46).
2. **Retrieval multi-hop thiếu tài liệu thứ hai** — với `RERANK_TOP_K = 3`, các câu cần hai chính sách
   (IDs 21, 33, 37, 40) chỉ nhận chunk của một chính sách.
3. **CP thấp một phần do cách chấm** — IDs 26, 28, 36 có CR = 1.0 nhưng CP = 0 (xem phần matrix).

## Bẫy xung đột phiên bản và giới hạn

| ID | Bẫy | Hành vi của answer | F | AR | CP | CR | avg | Kết luận |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 41 | Phiên bản: 12 vs 15 ngày | Trả 12 ngày (v2023 hết hiệu lực), trộn với quy tắc thâm niên v2024 | 1.0000 | 0.8603 | 0.0000 | 0.3333 | 0.5484 | Sai |
| 42 | Phiên bản: mốc 5 năm vs 3 năm | Liệt kê cả hai mốc, không chỉ ra bản hiện hành | 1.0000 | 0.8376 | 0.0000 | 0.3333 | 0.5427 | Không giải quyết |
| 43 | Phiên bản: 8 vs 12 ký tự | Nêu cả hai, gán đúng v1.0 cũ / v2.0 hiện hành | 1.0000 | 0.8703 | 0.8333 | 0.6667 | 0.8426 | Đúng |
| 44 | Phiên bản: 90 vs 120 ngày | Nêu cả hai theo tên file, không nói bản nào hiện hành | 1.0000 | 0.9050 | 0.5000 | 1.0000 | 0.8513 | Không giải quyết |
| 45 | Phiên bản: MFA | "Có, bắt buộc" theo v2.0 | 1.0000 | 0.7086 | 1.0000 | 0.5000 | 0.8021 | Đúng |
| 49 | Phiên bản: hỏi cả cũ và mới | 12 ngày (v2023) + nêu v2024 là bản hiện hành, thiếu 15 ngày | 0.6667 | 0.8813 | 0.0000 | 0.4000 | 0.4870 | Đúng một phần |
| 46 | Phủ định | "Không tìm thấy." | 0.0000 | 0.0000 | 1.0000 | 0.6667 | 0.4167 | Sai |
| 47 | Phủ định | "Không… tuyệt đối không tự ý xử lý" | 1.0000 | 0.9216 | 1.0000 | 0.6667 | 0.8971 | Đúng, thiếu báo cáo 1 giờ |
| 48 | Phủ định | "Không tìm thấy." | 0.0000 | 0.0000 | 1.0000 | 0.7500 | 0.4375 | Sai |
| 50 | Mâu thuẫn chính sách | "Không" + trích quy định cấm VPN cá nhân | 0.5000 | 0.8230 | 1.0000 | 0.7500 | 0.7682 | Đúng |

**Điều kiện Bonus Phase A về số liệu: đạt.** Adversarial mean avg_score 0.6594 < factual 0.8543
(chênh 0.1950), đo trên artifact hợp lệ ở trên.

Phân tích bẫy, tách khỏi điều kiện số:

- Nhóm version-conflict (IDs 41–45, 49) có mean 0.6790; nhóm phủ định/mâu thuẫn (46–48, 50) có
  mean 0.6299. Cả hai đều thấp hơn factual, nhưng hai câu kéo mean adversarial xuống nhiều nhất
  (46, 48) là lỗi từ chối ở bẫy phủ định, không phải version conflict.
- Pipeline **không** nhận ra version conflict ổn định: trong 6 câu phiên bản, 2 đúng (43, 45),
  1 đúng một phần (49), 3 sai hoặc không giải quyết (41, 42, 44).
- Ở ID 41, chunk v2024 "15 ngày" không được lấy; context 2 cũng thuộc bản cũ (đăng ký trước 3 ngày,
  ví dụ 14 ngày phép), khác bản v2024 (đăng ký trước 2 ngày).
- Bốn metric RAGAS không đo "đúng phiên bản": ID 41 có faithfulness = 1.0 vì answer được chunk
  v2023 trong contexts hỗ trợ; ID 44 có context_recall = 1.0 và avg 0.8513 dù không chọn bản hiện
  hành. Vì vậy adversarial thấp hơn chỉ cho thấy nhóm này khó hơn, không chứng minh pipeline phát
  hiện conflict. Phase B bổ sung điểm này: binary judge gán label 0 cho model_answer "12 ngày" của
  ID 41.

## Đề xuất sửa (kiểm tra được)

1. **Prompt generation:** cấm trả trống "Không tìm thấy." khi contexts có thông tin liên quan; trả
   lời phần có căn cứ và ghi rõ phần thiếu. Kiểm tra: chạy lại IDs 2, 21, 22, 23, 33, 46, 48,
   answer_relevancy > 0 và faithfulness tăng.
2. **Chunking:** trả parent chunk hoặc ghép chunk liền kề khi child kết thúc giữa câu. Kiểm tra:
   answer ID 46 chứa phủ định, ID 2 nêu 200.000.000 VNĐ/năm.
3. **Retrieval multi-hop:** tăng `RERANK_TOP_K` từ 3 lên 5 hoặc tách câu hỏi nhiều vế (query
   decomposition). Kiểm tra: mean CP/CR multi_hop và IDs 21, 33, 37, 40.
4. **Version-aware:** hạ hạng/lọc chunk có "Trạng thái: ĐÃ THAY THẾ" hoặc ngày hiệu lực cũ hơn bản
   cùng chủ đề ở cả dense và BM25; prompt yêu cầu nêu bản hiện hành khi có nhiều phiên bản. Kiểm tra:
   binary judge label = 1 cho IDs 41, 42, 44, 49.
5. **Đánh giá:** thêm binary correctness judge (helper Phase B) cho adversarial vì faithfulness không
   bắt được answer dùng bản cũ; với multi-hop, luôn đọc CP cùng CR.

## Giới hạn

- Evaluator dùng cùng họ model với generator; dù temperature = 0, kết quả vẫn dao động (ba câu NaN ở
  lượt đầu được chấm lại ở lượt sau).
- 50 câu, adversarial chỉ 10 câu: mean nhạy với 1–2 câu (46 và 48).
- Diagnosis/suggested_fix trong JSON là output Task 3 theo cây chẩn đoán cố định và được giữ nguyên;
  phần "Đọc lại" là phân tích thủ công và khác chẩn đoán tự động ở IDs 2, 21, 22, 23, 33, 46, 48.
- Answers được sinh trước; chưa chạy lại pipeline sau các đề xuất nên chưa có số đo cải thiện.