from __future__ import annotations

"""Phase B: LLM-as-Judge — pairwise, swap-and-average, Cohen κ, bias analysis."""

import json
import math
import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import JUDGE_MODEL, HUMAN_LABELS_PATH


@dataclass
class JudgeResult:
    question: str
    answer_a: str
    answer_b: str
    winner_pass1: str       # "A" | "B" | "tie"  (original order)
    winner_pass2: str       # "A" | "B" | "tie"  (after swap, ALREADY converted back)
    final_winner: str       # consensus after swap-and-average
    reasoning_pass1: str
    reasoning_pass2: str
    position_consistent: bool  # True if both passes agree on same answer
    scores_pass1: dict = field(default_factory=dict)  # {"A": float, "B": float}
    scores_pass2: dict = field(default_factory=dict)


def _clean_score(val) -> float:
    try:
        v = float(val)
    except (TypeError, ValueError):
        return 0.5
    if not math.isfinite(v):
        return 0.5
    if 1.0 < v <= 10.0:
        v = v / 10.0
    elif 10.0 < v <= 100.0:
        v = v / 100.0
    return max(0.0, min(1.0, v))


# ─── Task 5: Pairwise Judge ───────────────────────────────────────────────────

def pairwise_judge(question: str, answer_a: str, answer_b: str, reference: str = "") -> dict:
    """Task 5: Gọi LLM để chọn answer tốt hơn (A hoặc B) theo 3 tiêu chí."""
    from src.llm import gemini_openai_client
    client = gemini_openai_client()

    PROMPT_TEMPLATE = """Bạn là một chuyên gia đánh giá chất lượng câu trả lời RAG.

Câu hỏi: {question}
Chính sách/đáp án tham chiếu: {reference}

Answer A:
{answer_a}

Answer B:
{answer_b}

Hãy so sánh Answer A và Answer B dựa trên 3 tiêu chí:
1. Độ chính xác (accuracy): Có khớp với thông tin trong đáp án tham chiếu không?
2. Độ đầy đủ (completeness): Có trả lời đầy đủ các vế của câu hỏi không?
3. Tính súc tích (conciseness): Có lan man, dư thừa hay thiếu hụt không?

Chỉ trả về ĐÚNG MỘT đối tượng JSON hợp lệ theo định dạng (scores trong đoạn [0.0, 1.0]):
{{"winner": "A" hoặc "B" hoặc "tie", "reasoning": "Lý do lựa chọn ngắn gọn", "scores": {{"A": 0.0, "B": 0.0}}}}"""

    resp = client.chat.completions.create(
        model=JUDGE_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": "Bạn là giám khảo AI. Chỉ trả về duy nhất 1 JSON object hợp lệ."},
            {"role": "user", "content": PROMPT_TEMPLATE.format(
                question=question, answer_a=answer_a, answer_b=answer_b, reference=reference
            )},
        ],
        response_format={"type": "json_object"},
    )

    raw_content = resp.choices[0].message.content
    try:
        result = json.loads(raw_content)
    except json.JSONDecodeError:
        s = raw_content.lstrip()
        result, _ = json.JSONDecoder().raw_decode(s[s.find("{"):])

    winner = result.get("winner", "tie")
    if winner not in ("A", "B", "tie"):
        winner = "tie"

    raw_scores = result.get("scores") if isinstance(result.get("scores"), dict) else {}
    scores = {
        "A": _clean_score(raw_scores.get("A", 0.5)),
        "B": _clean_score(raw_scores.get("B", 0.5)),
    }
    reasoning = str(result.get("reasoning") or "").strip() or "Đánh giá dựa trên đáp án tham chiếu."

    return {
        "winner": winner,
        "reasoning": reasoning,
        "scores": scores,
    }


# ─── Task 6: Swap-and-Average ─────────────────────────────────────────────────

def swap_and_average(question: str, answer_a: str, answer_b: str, reference: str = "") -> JudgeResult:
    """Task 6: Chạy pairwise 2 lần (hoán đổi thứ tự), lấy kết quả nhất quán."""
    pass1 = pairwise_judge(question, answer_a, answer_b, reference=reference)
    pass2_raw = pairwise_judge(question, answer_b, answer_a, reference=reference)

    swap_map = {"A": "B", "B": "A", "tie": "tie"}
    winner_pass1 = pass1.get("winner", "tie")
    winner_pass2 = swap_map.get(pass2_raw.get("winner", "tie"), "tie")

    if winner_pass1 == winner_pass2:
        final = winner_pass1
    else:
        final = "tie"

    position_consistent = (winner_pass1 == winner_pass2)
    scores_p1 = pass1.get("scores", {"A": 0.0, "B": 0.0})
    scores_p2_raw = pass2_raw.get("scores", {"A": 0.0, "B": 0.0})

    return JudgeResult(
        question=question,
        answer_a=answer_a,
        answer_b=answer_b,
        winner_pass1=winner_pass1,
        winner_pass2=winner_pass2,
        final_winner=final,
        reasoning_pass1=pass1.get("reasoning", ""),
        reasoning_pass2=pass2_raw.get("reasoning", ""),
        position_consistent=position_consistent,
        scores_pass1={"A": _clean_score(scores_p1.get("A", 0.0)), "B": _clean_score(scores_p1.get("B", 0.0))},
        scores_pass2={"A": _clean_score(scores_p2_raw.get("B", 0.0)), "B": _clean_score(scores_p2_raw.get("A", 0.0))},
    )


# ─── Task 7: Cohen's κ ────────────────────────────────────────────────────────

def cohen_kappa(judge_labels: list[int], human_labels: list[int]) -> float:
    """Task 7: Tính Cohen's κ giữa LLM judge và human labels."""
    n = len(judge_labels)
    if n == 0 or len(human_labels) != n:
        return 0.0

    p_o = sum(1 for j, h in zip(judge_labels, human_labels) if j == h) / n
    p_e = (
        (judge_labels.count(1) / n) * (human_labels.count(1) / n) +
        (judge_labels.count(0) / n) * (human_labels.count(0) / n)
    )

    if p_e == 1.0:
        return 1.0

    return float((p_o - p_e) / (1 - p_e))


# ─── Task 8: Bias Report ──────────────────────────────────────────────────────

def bias_report(judge_results: list[JudgeResult]) -> dict:
    """Task 8: Đo lường position bias và verbosity bias."""
    total = len(judge_results)
    if total == 0:
        return {
            "total_judged": 0, "position_bias_rate": 0.0, "position_bias_count": 0,
            "verbosity_bias": 0.0, "verbosity_details": {
                "a_wins_a_longer": 0, "b_wins_b_longer": 0, "total_decisive": 0
            },
            "interpretation": "No data available."
        }

    position_bias_count = sum(1 for r in judge_results if not r.position_consistent)
    position_bias_rate = position_bias_count / total

    a_wins_a_longer = sum(
        1 for r in judge_results
        if r.final_winner == "A" and len(r.answer_a) > len(r.answer_b)
    )
    b_wins_b_longer = sum(
        1 for r in judge_results
        if r.final_winner == "B" and len(r.answer_b) > len(r.answer_a)
    )

    decisive = sum(1 for r in judge_results if r.final_winner in ("A", "B"))
    verbosity_bias = (a_wins_a_longer + b_wins_b_longer) / decisive if decisive > 0 else 0.0

    interpretation = (
        f"Position bias rate là {position_bias_rate:.1%}. "
        f"{'Điều này cho thấy LLM ưu tiên thiên lệch vị trí, kỹ thuật swap-and-average rất cần thiết.' if position_bias_rate > 0.3 else 'Position bias nằm ở mức thấp, đánh giá tương đối ổn định độc lập với vị trí.'} "
        f"Đồng thời, verbosity bias rate là {verbosity_bias:.1%}. "
        f"{'LLM có xu hướng ưu ái rõ rệt các câu trả lời dài hơn.' if verbosity_bias > 0.6 else 'Không có dấu hiệu LLM thiên vị quá mức cho câu trả lời dài.'}"
    )

    return {
        "total_judged": total,
        "position_bias_rate": round(position_bias_rate, 3),
        "position_bias_count": position_bias_count,
        "verbosity_bias": round(verbosity_bias, 3),
        "verbosity_details": {
            "a_wins_a_longer": a_wins_a_longer,
            "b_wins_b_longer": b_wins_b_longer,
            "total_decisive": decisive
        },
        "interpretation": interpretation,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from scripts.run_experiments import main
    raise SystemExit(main(["--phase", "b", *sys.argv[1:]]))