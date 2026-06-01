"""Run the matching eval across one or more LLM models.

Measures precision/recall on the match decision (score >= threshold) vs the
human label, score stability across repeats, and MAE vs human_score.

Usage:
    python -m eval.run --models qwen2.5:7b,gemma4:e2b --threshold 50 --repeats 2
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from jobhunt.config import default_config
from jobhunt.engine import recruteur
from jobhunt.llm import get_provider

DATASET = Path("eval/dataset.jsonl")
REPORT = Path("eval/report.json")


def _load_dataset() -> list[dict]:
    if not DATASET.exists():
        raise SystemExit(
            f"{DATASET} not found. Build it first (see eval/README.md), e.g. "
            "`python -m eval.seed_from_memory` then relabel by hand."
        )
    rows = []
    for line in DATASET.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("label") in ("match", "no_match") and row.get("text"):
            rows.append(row)
    if not rows:
        raise SystemExit("Dataset has no usable labelled rows (need label + text).")
    return rows


def _metrics(rows, preds, threshold):
    tp = fp = fn = tn = 0
    abs_err = []
    for row, pred in zip(rows, preds):
        truth = row["label"] == "match"
        guess = pred["score"] >= threshold
        if guess and truth:
            tp += 1
        elif guess and not truth:
            fp += 1
        elif not guess and truth:
            fn += 1
        else:
            tn += 1
        if row.get("human_score") is not None:
            abs_err.append(abs(pred["score"] - row["human_score"]))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    acc = (tp + tn) / len(rows) if rows else 0.0
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "accuracy": round(acc, 3),
        "mae": round(statistics.mean(abs_err), 1) if abs_err else None,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def evaluate_model(model: str, rows: list[dict], threshold: int, repeats: int) -> dict:
    cfg = default_config()
    cfg.llm.model = model
    provider = get_provider(cfg.llm)
    ok, msg = provider.health()
    if not ok:
        return {"model": model, "error": msg}

    all_scores: list[list[int]] = []
    last_preds = []
    for r in range(repeats):
        preds = []
        for row in rows:
            ev = recruteur.evaluate(provider, cfg, row["text"])
            preds.append(ev)
        last_preds = preds
        all_scores.append([p["score"] for p in preds])

    # stability: mean stdev of per-item scores across repeats
    stability = None
    if repeats > 1:
        per_item = [
            statistics.pstdev([all_scores[r][i] for r in range(repeats)])
            for i in range(len(rows))
        ]
        stability = round(statistics.mean(per_item), 2)

    result = {"model": model, "n": len(rows), "repeats": repeats, "score_stdev": stability}
    result.update(_metrics(rows, last_preds, threshold))
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="qwen2.5:7b", help="comma-separated Ollama model names")
    ap.add_argument("--threshold", type=int, default=50)
    ap.add_argument("--repeats", type=int, default=1)
    args = ap.parse_args()

    rows = _load_dataset()
    print(f"Dataset: {len(rows)} labelled rows · threshold {args.threshold} · repeats {args.repeats}\n")

    results = []
    for model in [m.strip() for m in args.models.split(",") if m.strip()]:
        print(f"→ {model} ...")
        res = evaluate_model(model, rows, args.threshold, args.repeats)
        results.append(res)
        if "error" in res:
            print(f"   ✗ {res['error']}")
        else:
            gate = "PASS ✅" if res["precision"] >= 0.70 else "FAIL ❌"
            print(f"   precision={res['precision']} recall={res['recall']} f1={res['f1']} "
                  f"acc={res['accuracy']} stdev={res['score_stdev']} mae={res['mae']}  GATE {gate}")

    REPORT.write_text(json.dumps({"threshold": args.threshold, "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport → {REPORT}")
    print("GATE (D1): ship-quality requires precision ≥ 0.70 on a reasonable local model.")


if __name__ == "__main__":
    main()
