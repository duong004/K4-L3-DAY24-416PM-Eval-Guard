from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json, math, hashlib, tempfile, re
from importlib.metadata import version
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY, GEMINI_MODEL, TEST_SET_PATH
from config import ARTIFACTS_DIR

RAGAS_BATCH_SIZE = 5
RAGAS_CHECKPOINT = os.path.join(ARTIFACTS_DIR, "ragas_50q.partial.json")


def _finite_score(value, *, metric: str = "unknown", index: int | None = None,
                  batch_range: str = "") -> float:
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        loc = f" (metric={metric}, row_index={index}, question_id={index + 1 if index is not None else '?'}, batch={batch_range})"
        raise ValueError(f"RAGAS returned non-numeric metric score: {value!r}{loc}") from exc
    if not math.isfinite(score) or not 0 <= score <= 1:
        loc = f" (metric={metric}, row_index={index}, question_id={index + 1 if index is not None else '?'}, batch={batch_range})"
        raise ValueError(f"RAGAS returned invalid metric score: {score!r}{loc}")
    return score


def _normalize_ragas_json_text(text: str) -> str:
    """Ensure valid JSON for RAGAS outputs when Gemini wraps schema or leaves inner quotes unescaped."""
    if not isinstance(text, str):
        return text
    stripped = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped, flags=re.IGNORECASE)
    candidate = fence_match.group(1).strip() if fence_match else stripped

    parsed = None
    try:
        parsed = json.loads(candidate)
    except Exception:
        if "verdict" in candidate and "reason" in candidate and candidate.lstrip().startswith("{"):
            v_match = re.search(r'"verdict"\s*:\s*([01]|true|false|"[01]")', candidate, flags=re.IGNORECASE)
            r_match = re.search(r'"reason"\s*:\s*"([\s\S]*?)"\s*,\s*"verdict"', candidate)
            if not r_match:
                r_match = re.search(r'"reason"\s*:\s*"([\s\S]*)"\s*\}', candidate)
            if v_match and r_match:
                raw_v = v_match.group(1).strip('"').lower()
                verdict_int = 1 if raw_v in ("1", "true") else 0
                reason_clean = r_match.group(1).replace('\\"', '"').strip()
                return json.dumps({"reason": reason_clean, "verdict": verdict_int}, ensure_ascii=False)
        return text

    if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
        if "verdict" in parsed[0] and not ({"statement", "statements"} & set(parsed[0])):
            parsed = parsed[0]

    if isinstance(parsed, dict):
        if "properties" in parsed and isinstance(parsed["properties"], dict) and "verdict" not in parsed:
            props = parsed["properties"]
            if "verdict" in props or "reason" in props:
                parsed = props
        if "verdict" in parsed or "reason" in parsed:
            if "verdict" in parsed:
                v = parsed["verdict"]
                if isinstance(v, bool):
                    parsed["verdict"] = 1 if v else 0
                elif isinstance(v, str) and v.strip() in ("0", "1"):
                    parsed["verdict"] = int(v.strip())
            if "verdict" in parsed and "reason" not in parsed:
                parsed["reason"] = str(parsed.get("explanation") or parsed.get("reasoning") or "Verified against context.")
            elif "reason" in parsed and not isinstance(parsed["reason"], str):
                parsed["reason"] = str(parsed["reason"])
            return json.dumps(parsed, ensure_ascii=False)
    return text


def _log_raw_output(text):
    path = os.environ.get("RAGAS_RAW_LOG")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as stream:
        stream.write(json.dumps({"raw": text}, ensure_ascii=False) + "\n")


def _normalize_chat_result(chat_result):
    for gen in getattr(chat_result, "generations", []):
        if hasattr(gen, "message") and isinstance(getattr(gen.message, "content", None), str):
            _log_raw_output(gen.message.content)
            fixed = _normalize_ragas_json_text(gen.message.content)
            gen.message.content = fixed
            if hasattr(gen, "text"):
                try:
                    gen.text = fixed
                except Exception:
                    pass
    return chat_result


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS in resumable batches so completed API work survives quota limits."""
    metric_names = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
    if not GEMINI_API_KEY:
        raise ValueError("Set GEMINI_API_KEY in .env to run RAGAS evaluation")
    if not (len(questions) == len(answers) == len(contexts) == len(ground_truths)):
        raise ValueError("RAGAS input lists must have the same length")
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
    from ragas.run_config import RunConfig
    from ragas.llms import LangchainLLMWrapper
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from src.llm import gemini_chat_model

    signature = hashlib.sha256(json.dumps({
        "questions": questions, "answers": answers, "contexts": contexts,
        "ground_truths": ground_truths, "model": GEMINI_MODEL,
        "metrics": metric_names, "ragas_version": version("ragas"),
    }, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    cached = {}
    if os.path.exists(RAGAS_CHECKPOINT):
        with open(RAGAS_CHECKPOINT, encoding="utf-8") as stream:
            checkpoint = json.load(stream)
        if checkpoint.get("input_sha256") == signature:
            cached = {
                int(index): {
                    **row,
                    **{name: _finite_score(row[name], metric=name, index=int(index), batch_range="checkpoint")
                       for name in metric_names}
                }
                for index, row in checkpoint.get("rows", {}).items()
            }
            print(f"[RAGAS] Loaded {len(cached)}/{len(questions)} cached rows from checkpoint.", flush=True)

    def save_checkpoint():
        os.makedirs(ARTIFACTS_DIR, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=ARTIFACTS_DIR, prefix="ragas_50q.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump({"input_sha256": signature,
                           "evaluator_models": [GEMINI_MODEL, "BAAI/bge-m3"],
                           "rows": {str(index): row for index, row in cached.items()}},
                          stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write("\n")
            os.replace(temp_path, RAGAS_CHECKPOINT)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    answer_relevancy.strictness = 1
    if hasattr(context_precision, "context_precision_prompt") and hasattr(
        context_precision.context_precision_prompt, "instruction"
    ):
        extra_rule = (
            "\nIMPORTANT: Return ONLY a valid JSON object with BOTH required keys: "
            "\"reason\" (non-empty string; use single quotes instead of double quotes inside the text) "
            "and \"verdict\" (integer 0 or 1). Do NOT wrap the output in a \"properties\" key."
        )
        if "BOTH required keys" not in context_precision.context_precision_prompt.instruction:
            context_precision.context_precision_prompt.instruction += extra_rule

    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
    base_chat_model = gemini_chat_model(temperature=0)
    orig_gen = base_chat_model._generate
    orig_agen = base_chat_model._agenerate

    def norm_gen(*args, **kwargs):
        return _normalize_chat_result(orig_gen(*args, **kwargs))

    async def norm_agen(*args, **kwargs):
        return _normalize_chat_result(await orig_agen(*args, **kwargs))

    object.__setattr__(base_chat_model, "_generate", norm_gen)
    object.__setattr__(base_chat_model, "_agenerate", norm_agen)

    llm = LangchainLLMWrapper(base_chat_model)
    # Context Precision: yêu cầu Gemini trả JSON object (reason: str, verdict: 0/1).
    # Chỉ ép định dạng output; không tự gán điểm khi lỗi.
    cp_chat_model = gemini_chat_model(temperature=0)
    cp_chat_model.model_kwargs = {**(cp_chat_model.model_kwargs or {}),
                                  "response_format": {"type": "json_object"}}
    cp_orig_gen = cp_chat_model._generate
    cp_orig_agen = cp_chat_model._agenerate

    def cp_norm_gen(*args, **kwargs):
        return _normalize_chat_result(cp_orig_gen(*args, **kwargs))

    async def cp_norm_agen(*args, **kwargs):
        return _normalize_chat_result(await cp_orig_agen(*args, **kwargs))

    object.__setattr__(cp_chat_model, "_generate", cp_norm_gen)
    object.__setattr__(cp_chat_model, "_agenerate", cp_norm_agen)
    context_precision.llm = LangchainLLMWrapper(cp_chat_model)
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3", model_kwargs={"device": "cpu"})
    run_config = RunConfig(max_workers=1, max_retries=2, timeout=120)
    missing = [index for index in range(len(questions)) if index not in cached]
    all_failures = []
    for chunk_start in range(0, len(missing), RAGAS_BATCH_SIZE):
        chunk = missing[chunk_start:chunk_start + RAGAS_BATCH_SIZE]
        batch_label = "IDs " + ",".join(str(index + 1) for index in chunk)
        print(f"[RAGAS] Running {batch_label}...", flush=True)
        dataset = Dataset.from_dict({
            "question": [questions[i] for i in chunk],
            "answer": [answers[i] for i in chunk],
            "contexts": [contexts[i] for i in chunk],
            "ground_truth": [ground_truths[i] for i in chunk],
        })
        result = evaluate(dataset, metrics=metrics, llm=llm, embeddings=embeddings,
                          run_config=run_config)
        rows = result.to_pandas().to_dict(orient="records")
        if len(rows) != len(chunk):
            raise ValueError(f"RAGAS returned {len(rows)} rows for {batch_label}")
        failures = []
        for index, row in zip(chunk, rows):
            scores, bad = {}, []
            for name in metric_names:
                try:
                    scores[name] = _finite_score(row[name], metric=name, index=index,
                                                 batch_range=batch_label)
                except ValueError as exc:
                    bad.append(str(exc))
            if bad:
                failures.extend(bad)
                continue
            cached[index] = {
                "question": questions[index], "answer": answers[index],
                "contexts": contexts[index], "ground_truth": ground_truths[index],
                **scores,
            }
        save_checkpoint()
        print(f"[RAGAS] Checkpoint: {len(cached)}/{len(questions)} câu hợp lệ đã lưu.", flush=True)
        all_failures.extend(failures)

    if all_failures:
        raise ValueError("RAGAS invalid scores (các câu hợp lệ đã lưu):\n" + "\n".join(all_failures))
    if len(cached) != len(questions):
        raise ValueError(f"RAGAS checkpoint has {len(cached)} rows for {len(questions)} questions")
    per_question = [EvalResult(**cached[index]) for index in range(len(questions))]
    aggregate = {name: _finite_score(sum(getattr(row, name) for row in per_question) / len(per_question),
                                     metric=name, batch_range="aggregate")
                 for name in metric_names}
    return {**aggregate, "evaluation_status": "completed",
            "metadata": {"evaluator_models": [GEMINI_MODEL, "BAAI/bge-m3"]},
            "per_question": per_question}


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    diagnostic_tree = {
        "faithfulness": ("Answer may contain claims unsupported by retrieved context.",
                         "Tighten the context only prompt and lower generation temperature."),
        "context_recall": ("Retrieved context is missing facts needed for the answer.",
                           "Improve chunk boundaries and add lexical BM25 coverage."),
        "context_precision": ("Retrieved context contains irrelevant chunks.",
                              "Rerank candidates and filter by document metadata."),
        "answer_relevancy": ("Answer does not directly address the question.",
                             "Improve the answer prompt and preserve the user question."),
    }
    metrics = tuple(diagnostic_tree)
    ranked = sorted(eval_results, key=lambda row: sum(getattr(row, m) for m in metrics) / len(metrics))
    failures = []
    for row in ranked[:max(0, bottom_n)]:
        worst = min(metrics, key=lambda name: getattr(row, name))
        diagnosis, suggested_fix = diagnostic_tree[worst]
        failures.append({
            "question": row.question, "answer": row.answer,
            "contexts": row.contexts, "ground_truth": row.ground_truth,
            "worst_metric": worst, "score": float(getattr(row, worst)),
            "average_score": sum(getattr(row, m) for m in metrics) / len(metrics),
            "diagnosis": diagnosis, "suggested_fix": suggested_fix,
            "error_tree": f"Answer incorrect/unsupported → inspect retrieved context → "
                          f"{'context incomplete' if worst == 'context_recall' else 'inspect query and ranking'} → {suggested_fix}",
        })
    return failures


def _json_default(obj):
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if hasattr(obj, "item"):
        return obj.item()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def save_report(results: dict, failures: list[dict], path: str = "reports/ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    report = {
        "aggregate": {k: float(v) if isinstance(v, (int, float)) else v
                      for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=_json_default)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")