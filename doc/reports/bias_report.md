# Đánh giá LLM Judge Phase B

Nhóm: 416PM

Người phụ trách: Tạ Đăng Dương - 2A202603018

Nguồn: `artifacts/judge_results.json`; run timestamp: `2026-10-13T04:28:15.383273+00:00`.
Models generation/judge: `generation = ["gemini-3.5-flash-lite"]`, `judge = ["gemini-3.5-flash-lite"]`.

## Năm cặp A/B và hai lượt

Nguồn cố định: A từ `artifacts/answers_50q.json:answer`; B từ `fixtures/human_labels_10q.json:model_answer`; reference từ `fixtures/test_set_50q.json:ground_truth`.
Ids: 1, 5, 12, 21, 41. Không đổi nguồn sau khi xem kết quả judge.

| ID | Candidate A (`answers_50q.json`) | Candidate B (`human_labels_10q.json`) | Pass 1 (A/B) | Pass 2 (đã quy về A/B gốc) | Final Winner | Position Consistent | Scores Pass 1 (A / B) | Scores Pass 2 (A / B) | Tóm tắt Reasoning hai lượt |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | Nhân viên được nghỉ **3 ngày làm việc** khi kết hôn. | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | B | B | B | true | 0.8 / 1.0 | 0.8 / 1.0 | Cả hai lượt đều chọn B vì B nêu đầy đủ chi tiết quan trọng "có lương" khớp với đáp án tham chiếu, trong khi A thiếu chi tiết này. |
| 5 | Muốn mua thiết bị trị giá 55 triệu cần Tổng Giám đốc (CEO) phê duyệt. | Cần Giám đốc phòng ban phê duyệt. | A | A | A | true | 1.0 / 0.0 | 1.0 / 0.2 | Cả hai lượt đều chọn A vì đơn hàng 55 triệu vượt mốc 50 triệu nên cần CEO phê duyệt theo đúng tham chiếu; B trả lời sai thẩm quyền. |
| 12 | 1 tháng lương. | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | B | B | B | true | 0.9 / 1.0 | 0.9 / 1.0 | Cả hai lượt đều đánh giá B cao hơn vì B diễn đạt thành câu hoàn chỉnh, rõ ràng và tự nhiên hơn cụm từ cụt lủn của A. |
| 21 | Dựa trên context, nhân viên có 9 năm thâm niên được 18 ngày phép (15 + 3). Thông tin về "lương trong khoảng nào" không tìm thấy trong context. | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | B | B | B | true | 0.5 / 1.0 | 0.5 / 1.0 | Cả hai lượt đều chọn B vì B trả lời đúng và đủ cả 2 vế (18 ngày phép và khung lương Senior 20–35 triệu), còn A bỏ sót vế lương. |
| 41 | Dựa trên context, mỗi nhân viên chính thức được hưởng 12 ngày phép năm có lương (ngoài ra, nhân viên có thâm niên từ 3 năm trở lên được cộng thêm 1 ngày phép cho mỗi 3 năm làm việc liên tục). | Nhân viên được nghỉ 12 ngày phép năm. | A | A | A | true | 0.5 / 0.3 | 0.6 / 0.4 | Cả hai câu đều mắc lỗi dùng con số 12 ngày của chính sách v2023 cũ thay vì 15 ngày của v2024, nhưng A được chọn ở cả hai lượt vì cung cấp thêm đúng quy tắc cộng phép thâm niên (1 ngày/3 năm). |

Position bias count/rate: `0 / 5` (`0.0%`, tương ứng `position_bias_rate = 0.0`).
Verbosity win rate: `0.8` (`80.0%`); decisive cases: `5` (`a_wins_a_longer = 2`, `b_wins_b_longer = 2`, `total_decisive = 5`).

**Phân tích chi tiết thiên lệch vị trí (Position Bias) và độ dài (Verbosity Bias):**
- **Về Position Bias (`0.0%`):** Trong toàn bộ 5 cặp câu hỏi (10 lượt gọi API với thứ tự `(A, B)` ở Pass 1 và `(B, A)` ở Pass 2), sau khi ánh xạ nhãn thắng của Pass 2 ngược về không gian A/B ban đầu, kết quả hoàn toàn đồng nhất ở cả 5 câu (`position_consistent = true` cho tất cả các ID 1, 5, 12, 21, 41). Không có trường hợp nào bị buộc gán `tie` do bất đồng giữa hai lượt.
- **Về Verbosity Bias (`80.0%` trên 5 decisive cases):** Về mặt thống kê thuần túy, có 4/5 cặp câu trả lời dài hơn giành chiến thắng (A thắng và dài hơn B ở ID 5, 41; B thắng và dài hơn A ở ID 1, 12), chỉ có ID 21 là B ngắn hơn A (83 ký tự so với 140 ký tự) nhưng B vẫn thắng. Tuy nhiên, khi đọc kỹ nội dung từng cặp, con số 80% này phần lớn phản ánh **độ đầy đủ thông tin (completeness)** chứ không phải thiên lệch độ dài mù quáng:
  - Ở **ID 1** và **ID 12**, B dài hơn A vì B bổ sung từ khóa thiết yếu `"có lương"` và viết thành câu hoàn chỉnh thay vì chỉ viết cụt lủn `"1 tháng lương."`.
  - Ở **ID 5**, A dài hơn B (69 ký tự so với 33 ký tự) vì A lặp lại câu hỏi và nêu đúng chức danh `"Tổng Giám đốc (CEO)"`, trong khi B trả lời sai hoàn toàn (`"Giám đốc phòng ban"`).
  - Ở **ID 21**, dù A dài hơn do chứa câu giải thích không tìm thấy thông tin trong context, Judge vẫn chấm B thắng tuyệt đối (`1.0` so với `0.5`) vì B cung cấp đúng khung lương 20–35 triệu VNĐ.
  - Dấu hiệu thiên lệch độ dài thực sự chỉ xuất hiện ở **ID 41**: cả A và B đều sai bản chất khi lấy số ngày phép cơ bản là 12 ngày (theo chính sách v2023 đã hết hiệu lực, thay vì 15 ngày theo v2024). Khi buộc phải so sánh hai câu cùng sai ý chính trong pairwise prompt, LLM Judge có xu hướng ưu ái câu A dài hơn vì chứa thêm thông tin phụ về thâm niên (cộng 1 ngày cho mỗi 3 năm). Điều này chứng minh pairwise judge chỉ cho biết câu nào *tốt hơn tương đối* giữa hai ứng viên, không thể thay thế đánh giá nhị phân (0/1) theo chuẩn tham chiếu.

## Calibration đúng model_answer

Helper `judge_binary` đánh giá đúng `question` và `model_answer` đang có trong `fixtures/human_labels_10q.json`; không lấy answer mới của pipeline. Prompt chỉ nhận `question`, `answer`, `reference`. Không gửi `human_label`, `human_note` hoặc phân bố nhãn human vào prompt.

| Thứ tự | Question ID | `model_answer` gốc (`human_labels_10q.json`) | Judge Label | Human Label | Agree | Reasoning của Judge |
|---:|---:|---|---:|---:|---|---|
| 1 | 1 | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | 1 | 1 | Đúng | Answer trả lời đúng và đủ ý thiết yếu của câu hỏi dựa trên reference, có đề cập đến số ngày nghỉ và lương. |
| 2 | 5 | Cần Giám đốc phòng ban phê duyệt. | 0 | 0 | Đúng | Answer sai vì theo reference đơn hàng trên 50 triệu cần Tổng Giám đốc (CEO) phê duyệt, nhưng answer lại nêu là Giám đốc phòng ban. |
| 3 | 12 | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | 1 | 1 | Đúng | Answer trả lời chính xác và đầy đủ ý thiết yếu theo reference, nêu rõ mức thưởng Tết tối thiểu là 1 tháng lương cho đối tượng được hỏi. |
| 4 | 21 | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | 1 | 1 | Đúng | Câu trả lời đáp ứng chính xác số ngày phép (18 ngày) và khoảng lương (20-35 triệu) theo đúng chính sách v2024 trong reference. |
| 5 | 23 | Hoàn trả 25 triệu vì chưa đủ 1 năm cam kết. | 1 | 1 | Đúng | Câu trả lời đã chính xác theo reference, trả lời đúng số tiền phải hoàn trả (25 triệu) và lýzahlen (nghỉ sau 8 tháng là chưa đủ 1 năm cam kết), không bỏ sót ý thiết yếu. |
| 6 | 29 | Trưởng phòng phê duyệt. Phạt 2% tháng trên 8 triệu. | 0 | 0 | Đúng | Thiếu người phê duyệt (cần Trưởng phòng + Kế toán trưởng) và tính sai phí phạt (thiếu công thức pro-rata 15 ngày quá hạn = 80.000 VNĐ). |
| 7 | 33 | Phép: 19 ngày. Phụ cấp: 1.500.000 VNĐ/tháng. | 1 | 1 | Đúng | Answer trả lời đúng và đủ số ngày phép năm (19 ngày) và tổng phụ cấp hàng tháng (1.500.000 VNĐ) theo đúng reference. |
| 8 | 41 | Nhân viên được nghỉ 12 ngày phép năm. | 0 | 0 | Đúng | Câu trả lời sử dụng thông tin từ chính sách v2023 đã bị thay thế (12 ngày) thay vì dùng chính sách v2024 hiện hành (15 ngày cơ bản). |
| 9 | 46 | Nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần. | 1 | 1 | Đúng | Câu trả lời hoàn toàn chính xác theo reference, nêu đúng nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần, tuân thủ đúng phủ định. |
| 10 | 50 | Được, miễn là đảm bảo kết nối an toàn. | 0 | 0 | Đúng | Reference cấm sử dụng VPN cá nhân, nhưng answer lại trả lời là được phép, sai hoàn toàn so với chính sách. |

Cohen’s κ: `1.0`.
Observed/chance agreement và diễn giải:
- Tổng số mẫu đánh giá: $N = 10$.
- Tỷ lệ đồng thuận quan sát được (Observed Agreement): $p_o = \frac{10}{10} = 1.0$ (Judge và Human đồng thuận tuyệt đối trên cả 6 câu nhãn `1` và 4 câu nhãn `0`).
- Xác suất đồng thuận ngẫu nhiên (Chance Agreement):
  $$p_e = P(\text{Judge}=1)\cdot P(\text{Human}=1) + P(\text{Judge}=0)\cdot P(\text{Human}=0) = \left(\frac{6}{10}\times\frac{6}{10}\right) + \left(\frac{4}{10}\times\frac{4}{10}\right) = 0.36 + 0.16 = 0.52$$
- Hệ số Cohen's $\kappa$:
  $$\kappa = \frac{p_o - p_e}{1 - p_e} = \frac{1.0 - 0.52}{1.0 - 0.52} = 1.0$$
- Theo thang đo Landis-Koch, $\kappa = 1.0$ nằm trong khoảng $0.8 - 1.0$ (*Almost Perfect Agreement*), vượt xa ngưỡng $\kappa > 0.6$ của yêu cầu bài lab và đủ điều kiện đạt Bonus Phase B (+3 điểm). Đặc biệt ở câu ID 41, trong khi pairwise judge buộc phải chọn A thắng B dù cả hai cùng dùng chính sách cũ v2023, binary judge đã chấm chính xác `label = 0` vì phát hiện câu trả lời dùng phiên bản v2023 đã hết hiệu lực.

## Giới hạn và cách dùng judge

- **Quy mô mẫu nhỏ:** Bộ dữ liệu hiệu chuẩn chỉ gồm 10 câu cho binary calibration và 5 cặp cho pairwise evaluation. Dù đạt $\kappa = 1.0$ và `position_bias_rate = 0.0` trên tập mẫu này, kết quả thống kê trên 5–10 mẫu vẫn có phương sai lớn và chưa đảm bảo LLM Judge không mắc lỗi trên tập dữ liệu sản phẩm hàng nghìn câu.
- **Đặc thù của model và prompt:** Cả hệ thống sinh câu trả lời (generation) và giám khảo (judge) đều đang dùng chung họ mô hình `gemini-3.5-flash-lite` ở `temperature = 0`. Việc dùng cùng một model family có nguy cơ tạo ra thiên lệch tự ưa thích (self-preference bias) đối với văn phong của chính model đó.
- **Không coi LLM Judge là chân lý tuyệt đối:** Thực nghiệm ở câu ID 41 cho thấy pairwise judge có thể cho điểm `0.5 - 0.6` và tuyên bố người thắng ngay cả khi cả hai ứng viên đều trích dẫn sai phiên bản chính sách (12 ngày thay vì 15 ngày). Do đó, trong môi trường production, cần kết hợp binary judge có neo chặt vào `ground_truth` (reference-anchored) để kiểm tra tính đúng đắn, dùng kỹ thuật `swap_and_average` để triệt tiêu position bias khi so sánh A/B, và duy trì lấy mẫu kiểm toán thủ công bởi con người (human-in-the-loop) định kỳ trên các câu có điểm thấp hoặc kết quả `tie`.