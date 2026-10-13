# Đánh giá LLM Judge Phase B

Nhóm: 416PM

Người phụ trách: Tạ Đăng Dương - 2A202603018

Nguồn: `artifacts/judge_results.json`; run timestamp: `2026-10-13T04:42:15.383273+00:00`.
Models generation/judge: `generation = ["gemini-3.5-flash-lite"]`, `judge = ["gemini-3.5-flash-lite"]`.

## Năm cặp A/B và hai lượt

Nguồn cố định: A từ `artifacts/answers_50q.json:answer`; B từ `fixtures/human_labels_10q.json:model_answer`; reference từ `fixtures/test_set_50q.json:ground_truth`.
Ids: 1, 5, 12, 21, 41. Không đổi nguồn sau khi xem kết quả judge.

| ID | Candidate A (`answers_50q.json`) | Candidate B (`human_labels_10q.json`) | Pass 1 (A/B) | Pass 2 (đã quy về A/B gốc) | Final Winner | Position Consistent | Scores Pass 1 (A / B) | Scores Pass 2 (A / B) | Tóm tắt Reasoning hai lượt |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | Nhân viên được nghỉ **3 ngày làm việc** khi kết hôn. | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | B | B | B | true | 0.8 / 1.0 | 0.8 / 1.0 | Cả hai lượt chọn câu có chi tiết "có lương" khớp reference (B gốc); A thiếu chi tiết này. |
| 5 | Muốn mua thiết bị trị giá 55 triệu cần Tổng Giám đốc (CEO) phê duyệt. | Cần Giám đốc phòng ban phê duyệt. | A | A | A | true | 1.0 / 0.0 | 1.0 / 0.2 | Cả hai lượt chọn A vì 55 triệu vượt mốc 50 triệu nên cần CEO theo reference; B sai thẩm quyền. |
| 12 | 1 tháng lương. | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | B | B | B | true | 0.9 / 1.0 | 0.9 / 1.0 | Cả hai đúng nội dung; judge chọn B vì là câu hoàn chỉnh, rõ hơn cụm từ ngắn của A. |
| 21 | Dựa trên context, nhân viên có 9 năm thâm niên được 18 ngày phép (15 + 3). Thông tin về "lương trong khoảng nào" không tìm thấy trong context. | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | B | B | B | true | 0.5 / 1.0 | 0.5 / 1.0 | Cả hai lượt chọn B vì trả lời đủ hai vế (18 ngày phép và khung lương Senior 20–35 triệu); A bỏ sót vế lương. |
| 41 | Dựa trên context, mỗi nhân viên chính thức được hưởng 12 ngày phép năm có lương (ngoài ra, nhân viên có thâm niên từ 3 năm trở lên được cộng thêm 1 ngày phép cho mỗi 3 năm làm việc liên tục). | Nhân viên được nghỉ 12 ngày phép năm. | A | A | A | true | 0.5 / 0.3 | 0.6 / 0.4 | Cả hai câu cùng dùng 12 ngày của v2023 thay vì 15 ngày của v2024; A được chọn vì thêm quy tắc thâm niên. Reasoning lượt 2 tự mâu thuẫn (xem bên dưới). |

Lưu ý khi đọc `reasoning_pass2` trong JSON: lượt 2 gửi thứ tự (B, A), nên "Answer A"/"Answer B"
trong reasoning lượt 2 là nhãn theo thứ tự đã đổi chỗ. Winner và scores lượt 2 đã được quy về A/B gốc.

Position bias count/rate: `0 / 5` (`0.0%`, tương ứng `position_bias_rate = 0.0`).
Verbosity win rate: `0.8` (`80.0%`); decisive cases: `5` (`a_wins_a_longer = 2`, `b_wins_b_longer = 2`, `total_decisive = 5`).

**Phân tích Position Bias và Verbosity Bias:**

- **Position Bias (`0.0%`):** Trong 5 cặp (10 lượt gọi, thứ tự `(A, B)` ở lượt 1 và `(B, A)` ở lượt 2), sau khi quy winner lượt 2 về A/B gốc, cả 5 cặp đều nhất quán (`position_consistent = true` cho IDs 1, 5, 12, 21, 41). Không cặp nào bị gán `tie` do hai lượt bất đồng. Với 5 cặp, kết quả này không loại trừ position bias trên tập lớn hơn.
- **Verbosity Bias (`80.0%` trên 5 decisive cases):** 4/5 cặp có câu dài hơn thắng (A thắng và dài hơn ở IDs 5, 41; B thắng và dài hơn ở IDs 1, 12). Riêng ID 21, A dài hơn nhưng B thắng. Đọc nội dung từng cặp cho thấy con số 80% phần lớn phản ánh **độ đầy đủ** chứ không phải ưu ái độ dài thuần túy:
  - **ID 1** và **ID 12:** B dài hơn vì có thêm chi tiết thiết yếu "có lương" (ID 1) hoặc là câu hoàn chỉnh thay vì cụm "1 tháng lương." (ID 12).
  - **ID 5:** A dài hơn và đúng (CEO), B ngắn và sai (Giám đốc phòng ban); A thắng vì đúng.
  - **ID 21:** A dài hơn do có câu giải thích không tìm thấy thông tin, nhưng judge chấm B thắng (1.0 so với 0.5) vì B có khung lương 20–35 triệu.
  - **ID 41** là dấu hiệu verbosity thực sự: cả A và B cùng sai ý chính (12 ngày theo v2023 thay vì 15 ngày theo v2024). Khi buộc phải chọn giữa hai câu cùng sai, judge chọn câu A dài hơn vì có thêm thông tin phụ về thâm niên. Reasoning lượt 2 của cặp này còn tự mâu thuẫn ("Đợi chút…", đổi ý giữa chừng) dù winner cuối cùng nhất quán. Pairwise judge chỉ cho biết câu nào *tốt hơn tương đối*, không thay được đánh giá nhị phân 0/1 theo reference.
- **Self-preference:** Candidate A do cùng model `gemini-3.5-flash-lite` sinh ra, nhưng judge chọn A chỉ 2/5 cặp (IDs 5, 41) và chọn B 3/5. Trên mẫu này không thấy dấu hiệu judge ưu ái output của chính họ model.

## Calibration đúng model_answer

Helper `judge_binary` đánh giá đúng `question` và `model_answer` đang có trong `fixtures/human_labels_10q.json`; không lấy answer mới của pipeline. Prompt chỉ nhận `question`, `answer`, `reference`. Không gửi `human_label`, `human_note` hoặc phân bố nhãn human vào prompt.

| Thứ tự | Question ID | `model_answer` gốc (`human_labels_10q.json`) | Judge Label | Human Label | Agree | Reasoning của Judge |
|---:|---:|---|---:|---:|---|---|
| 1 | 1 | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | 1 | 1 | Đúng | Answer trả lời đúng và đủ ý thiết yếu của câu hỏi dựa trên reference, có đề cập đến số ngày nghỉ và lương. |
| 2 | 5 | Cần Giám đốc phòng ban phê duyệt. | 0 | 0 | Đúng | Answer sai vì theo reference đơn hàng trên 50 triệu cần Tổng Giám đốc (CEO) phê duyệt, nhưng answer lại nêu là Giám đốc phòng ban. |
| 3 | 12 | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | 1 | 1 | Đúng | Answer trả lời chính xác và đầy đủ ý thiết yếu theo reference, nêu rõ mức thưởng Tết tối thiểu là 1 tháng lương cho đối tượng được hỏi. |
| 4 | 21 | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | 1 | 1 | Đúng | Câu trả lời đáp ứng chính xác số ngày phép (18 ngày) và khoảng lương (20-35 triệu) theo đúng chính sách v2024 trong reference. |
| 5 | 23 | Hoàn trả 25 triệu vì chưa đủ 1 năm cam kết. | 1 | 1 | Đúng | Câu trả lời đã chính xác theo reference, trả lời đúng số tiền phải hoàn trả (25 triệu) và lý do (nghỉ sau 8 tháng là chưa đủ 1 năm cam kết), không bỏ sót ý thiết yếu. |
| 6 | 29 | Trưởng phòng phê duyệt. Phạt 2% tháng trên 8 triệu. | 0 | 0 | Đúng | Thiếu người phê duyệt (cần Trưởng phòng + Kế toán trưởng) và tính sai phí phạt (theo reference, quá hạn 30 ngày phải là phí phạt của toàn bộ thời gian quá hạn, hoặc cụ thể reference tính cho 15 ngày là 80.000 VNĐ, trả lời 2% tháng trên 8 triệu là thiếu công thức và sai thời gian tính phạt). |
| 7 | 33 | Phép: 19 ngày. Phụ cấp: 1.500.000 VNĐ/tháng. | 1 | 1 | Đúng | Answer trả lời đúng và đủ số ngày phép năm (19 ngày) và tổng phụ cấp hàng tháng (1.500.000 VNĐ) theo đúng reference. |
| 8 | 41 | Nhân viên được nghỉ 12 ngày phép năm. | 0 | 0 | Đúng | Câu trả lời sử dụng thông tin từ chính sách v2023 đã bị thay thế (12 ngày) thay vì dùng chính sách v2024 hiện hành (15 ngày cơ bản). |
| 9 | 46 | Nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần. | 1 | 1 | Đúng | Câu trả lời hoàn toàn chính xác theo reference, nêu đúng nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần, tuân thủ đúng phủ định. |
| 10 | 50 | Được, miễn là đảm bảo kết nối an toàn. | 0 | 0 | Đúng | Reference cấm sử dụng VPN cá nhân, nhưng answer lại trả lời là được phép, sai hoàn toàn so với chính sách. |

Cohen’s κ: `1.0`.
Observed/chance agreement và diễn giải:
- Tổng số mẫu: $N = 10$.
- Observed agreement: $p_o = \frac{10}{10} = 1.0$ (judge và human trùng nhau trên cả 6 câu nhãn `1` và 4 câu nhãn `0`).
- Chance agreement:
  $$p_e = P(\text{Judge}=1)\cdot P(\text{Human}=1) + P(\text{Judge}=0)\cdot P(\text{Human}=0) = \left(\frac{6}{10}\times\frac{6}{10}\right) + \left(\frac{4}{10}\times\frac{4}{10}\right) = 0.36 + 0.16 = 0.52$$
- Cohen's $\kappa$:
  $$\kappa = \frac{p_o - p_e}{1 - p_e} = \frac{1.0 - 0.52}{1.0 - 0.52} = 1.0$$
- $\kappa = 1.0$ thuộc khoảng $0.8 - 1.0$ (*almost perfect agreement*) theo thang Landis–Koch và vượt ngưỡng $\kappa > 0.6$ của điều kiện bonus Phase B. Ở ID 41, pairwise judge vẫn phải chọn một bên thắng dù cả hai cùng dùng v2023, còn binary judge chấm đúng `label = 0` cho model_answer "12 ngày" vì phát hiện phiên bản đã hết hiệu lực.

## Giới hạn và cách dùng judge

- **Mẫu nhỏ:** 10 câu cho calibration và 5 cặp cho pairwise. Với 10 nhãn phân bố 6/4, chỉ cần judge lệch 2 nhãn theo hai chiều ngược nhau thì κ đã giảm còn khoảng 0.58, dưới ngưỡng 0.6. $\kappa = 1.0$ và `position_bias_rate = 0.0` trên tập này chưa đảm bảo độ tin cậy trên tập lớn.
- **Cùng họ model:** generation và judge đều dùng `gemini-3.5-flash-lite` ở `temperature = 0`; rủi ro self-preference vẫn tồn tại dù chưa thấy trên 5 cặp.
- **Reasoning không phải bằng chứng:** reasoning lượt 2 của ID 41 tự mâu thuẫn dù winner nhất quán; chỉ nên dùng reasoning để đọc hiểu, không coi là lập luận đáng tin.
- **Không coi LLM judge là chân lý:** pairwise judge có thể cho điểm 0.5–0.6 và chọn người thắng khi cả hai ứng viên cùng sai (ID 41). Trong production nên kết hợp binary judge neo vào `ground_truth` để kiểm tra đúng/sai, giữ `swap_and_average` khi so sánh A/B, và lấy mẫu kiểm tra thủ công định kỳ trên các câu điểm thấp hoặc `tie`.