"""
Ragas-based evaluation pipeline for the Multimodal RAG system.

Usage:
    python eval/evaluate.py --kb-id <kb_uuid> --questions eval/sample_questions.json

Prerequisites:
    pip install ragas datasets openai
    OPENAI_API_KEY must be set.
    Backend must be running at http://localhost:8000.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import requests

THRESHOLDS = {
    "faithfulness": 0.85,
    "answer_relevancy": 0.80,
    "context_recall": 0.75,
    "context_precision": 0.70,
}


def query_sync(kb_id: str, question: str, base_url: str, api_key: str | None) -> dict:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    resp = requests.post(
        f"{base_url}/kb/{kb_id}/query",
        json={"query": question, "stream": False, "top_k": 20, "rerank_n": 5},
        headers=headers,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def collect_results(questions: list[dict], base_url: str, api_key: str | None) -> list[dict]:
    results = []
    for item in questions:
        kb_id = item.get("kb_id", "").strip()
        if not kb_id or kb_id.startswith("__"):
            print(f"  [skip] {item['id']} — no kb_id configured")
            continue

        print(f"  Querying {item['id']}: {item['question'][:60]}…")
        try:
            resp = query_sync(kb_id, item["question"], base_url, api_key)
            results.append({
                "question": item["question"],
                "answer": resp.get("answer", ""),
                "contexts": [s["excerpt"] for s in resp.get("sources", [])],
                "ground_truth": item.get("ground_truth", ""),
            })
        except Exception as exc:
            print(f"  [error] {item['id']}: {exc}")

    return results


def run_ragas(results: list[dict]) -> dict:
    try:
        from datasets import Dataset
        from ragas import evaluate as ragas_evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_recall, context_precision
    except ImportError:
        print("ERROR: Install ragas with: pip install ragas datasets")
        sys.exit(1)

    dataset = Dataset.from_list(results)
    scores = ragas_evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
    )
    return scores.to_pandas().mean().to_dict()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", default="eval/sample_questions.json")
    parser.add_argument("--kb-id", default=None, help="Override kb_id for all questions")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--api-key", default=os.getenv("RAG_API_KEY"))
    parser.add_argument("--output", default="eval/results.json")
    args = parser.parse_args()

    questions = json.loads(Path(args.questions).read_text())
    if args.kb_id:
        for q in questions:
            q["kb_id"] = args.kb_id

    print(f"Collecting responses from {args.base_url} ({len(questions)} questions)…")
    results = collect_results(questions, args.base_url, args.api_key)

    if not results:
        print("No results collected — check kb_id configuration in sample_questions.json")
        sys.exit(1)

    print(f"\nRunning Ragas evaluation on {len(results)} items…")
    scores = run_ragas(results)

    print("\n── Ragas Scores ──────────────────────────────")
    passed = True
    for metric, score in scores.items():
        threshold = THRESHOLDS.get(metric, 0.0)
        status = "PASS" if score >= threshold else "FAIL"
        if score < threshold:
            passed = False
        print(f"  {metric:<25} {score:.3f}  (threshold {threshold})  [{status}]")

    Path(args.output).write_text(json.dumps({"scores": scores, "details": results}, indent=2))
    print(f"\nDetailed results saved to {args.output}")

    if not passed:
        print("\nEvaluation FAILED — some metrics below threshold")
        sys.exit(1)

    print("\nEvaluation PASSED")


if __name__ == "__main__":
    main()
