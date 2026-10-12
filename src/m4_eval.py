from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json, math, hashlib, tempfile
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


def _finite_score(value) -> float:
    score = float(value)
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError(f"RAGAS returned invalid metric score: {score!r}")
    return score


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
                int(index): {**row, **{name: _finite_score(row[name]) for name in metric_names}}
                for index, row in checkpoint.get("rows", {}).items()
            }

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
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
    llm = LangchainLLMWrapper(gemini_chat_model(temperature=0))
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3", model_kwargs={"device": "cpu"})
    run_config = RunConfig(max_workers=1, max_retries=2, timeout=120)
    for start in range(0, len(questions), RAGAS_BATCH_SIZE):
        stop = min(start + RAGAS_BATCH_SIZE, len(questions))
        if all(index in cached for index in range(start, stop)):
            continue
        dataset = Dataset.from_dict({
            "question": questions[start:stop], "answer": answers[start:stop],
            "contexts": contexts[start:stop], "ground_truth": ground_truths[start:stop],
        })
        result = evaluate(dataset, metrics=metrics, llm=llm, embeddings=embeddings,
                          run_config=run_config)
        rows = result.to_pandas().to_dict(orient="records")
        if len(rows) != stop - start:
            raise ValueError(f"RAGAS returned {len(rows)} rows for batch {start}:{stop}")
        batch = {}
        for index, row in enumerate(rows, start):
            batch[index] = {
                "question": questions[index], "answer": answers[index],
                "contexts": contexts[index], "ground_truth": ground_truths[index],
                **{name: _finite_score(row[name]) for name in metric_names},
            }
        cached.update(batch)
        save_checkpoint()

    if len(cached) != len(questions):
        raise ValueError(f"RAGAS checkpoint has {len(cached)} rows for {len(questions)} questions")
    per_question = [EvalResult(**cached[index]) for index in range(len(questions))]
    aggregate = {name: _finite_score(sum(getattr(row, name) for row in per_question) / len(per_question))
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
