# Phân tích lỗi Phase A

**Trạng thái:** Chưa có `artifacts/ragas_50q.json`, nên chưa thể ghi điểm theo
nhóm, bottom 10 hay failure matrix và chưa xác nhận bonus. Không thay điểm thiếu
bằng giá trị giả.

## Bằng chứng lần chạy

- Setup live đã ghi `artifacts/answers_50q.json`: 50 câu, factual 20, multi_hop
  20, adversarial 10; cả 50 có `generation_mode=llm`, model
  `gemini-3.5-flash-lite`, contexts không rỗng.
- Chạy chẩn đoán Faithfulness ban đầu cho 11 answers ngắn xác nhận `NaN` ở IDs
  3, 5, 8 và 10. Bốn answer này đã được viết lại thành câu hoàn chỉnh từ
  question/context bằng Gemini và lưu vào `answers_50q.json`.
- Phase A sau đó xử lý hết 200 metric rows nhưng vẫn trả `NaN` vì RAGAS log
  `No statements were generated from the answer`. Runner giữ fail-closed và
  không ghi report. Một job Context Precision cũng báo output thiếu trường
  `reason`/`verdict`; tiến trình tiếp tục nhưng có thể đã tiêu tốn retry.
- Lượt vừa rồi chưa có checkpoint vì code checkpoint được thêm sau khi nó đã
  bắt đầu. m4 hiện chia đánh giá thành lô 5 câu, lưu các lô hợp lệ nguyên tử,
  tái sử dụng chúng khi input/model/RAGAS version khớp và giảm tối đa retry từ
  10 xuống 2. Lần chạy kế tiếp sẽ dùng checkpoint này; các metric còn `NaN`
  vẫn bị từ chối, không quy thành điểm 0.
- Một số lời gọi enrichment nhận 429 nên M5 dùng fallback cục bộ cho các chunks
  đó; log setup ghi lỗi từng lời gọi. Answers đầu ra vẫn ghi nhận generation
  mode/model riêng.
- Lượt Phase A gần nhất không ghi nhận 429, nhưng tổng request Gemini thực tế
  không được đo: 200 metric rows không đồng nghĩa 200 API requests, vì một số
  metric dùng nhiều prompt và retry. Vì vậy chưa thể khẳng định một ngày 500
  request đủ cho setup + Phase A. Không chạy lại setup; dùng answers đã lưu và
  checkpoint để chia Phase A qua nhiều ngày nếu quota hết.

## Điểm theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---:|---:|---:|
| faithfulness | Chưa lưu | Chưa lưu | Chưa lưu |
| answer_relevancy | Chưa lưu | Chưa lưu | Chưa lưu |
| context_precision | Chưa lưu | Chưa lưu | Chưa lưu |
| context_recall | Chưa lưu | Chưa lưu | Chưa lưu |
| avg_score | Chưa lưu | Chưa lưu | Chưa lưu |

## Bottom 10 và matrix

Chưa có kết quả được xác thực để trích bottom 10, diagnosis, suggested fix hoặc
matrix `worst_metric × distribution`. Nhóm yếu nhất phải được chọn theo mean
`avg_score` thấp nhất sau khi có report hợp lệ.

## Bẫy xung đột phiên bản và giới hạn

Fixture cố ý đặt các phiên bản quy định mâu thuẫn. Câu 41 hỏi số ngày phép mà
không nêu phiên bản: tài liệu 2023 quy định 12 ngày, còn bản 2024 thay thế nó
bằng 15 ngày. Câu 42 đặt mốc cộng phép 5 năm của bản cũ cạnh mốc 3 năm hiện
hành. Câu 43–45 kiểm tra chính sách mật khẩu: v1 yêu cầu 8 ký tự, đổi sau 90
ngày, không bắt buộc MFA; v2 yêu cầu 12 ký tự, đổi sau 120 ngày và bắt buộc
MFA.

Đây là cơ chế có thể kéo mean Adversarial xuống: truy xuất có thể trả cả bản cũ
và mới; câu trả lời có thể dùng bản hết hiệu lực hoặc trộn hai bản. M2 cộng điểm
cho tài liệu mới nhất trong BM25 nếu câu hỏi không chỉ rõ phiên bản, nhưng dense
search không áp dụng quy tắc đó; RRF hợp nhất hai danh sách. Câu 46–48 còn có
bẫy phủ định riêng, không nên quy mọi lỗi adversarial cho version conflict.

Đây mới là giả thuyết dựa trên fixture và mã. Chỉ khi Phase A ghi được mean thật
mới kết luận được Adversarial thấp hơn Factual hoặc xác nhận bonus. Khi quota
có lại, chạy `python scripts/run_experiments.py --phase a --live`; m4 sẽ nạp các
lô hợp lệ đã checkpoint và dừng nếu metric nào vẫn `NaN`. Sau đó cần đối chiếu
version-conflict IDs trong bottom 10 với kết quả thật.
