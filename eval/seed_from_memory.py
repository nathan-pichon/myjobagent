"""Seed an eval dataset skeleton from the legacy memory.json.

IMPORTANT: the old scores are PREDICTIONS, not ground truth. This only
pre-fills `text`/metadata; you MUST relabel `label` (match/no_match) by hand.
Since the legacy memory stored only metadata (not the raw page text), we emit
the available fields and leave `text` empty for manual paste, or you can
re-extract from the URL with the scrape extra.
"""
from __future__ import annotations

import json
from pathlib import Path

SRC = Path("memory.json")
OUT = Path("eval/dataset.seed.jsonl")


def main() -> None:
    if not SRC.exists():
        print("No memory.json found.")
        return
    data = json.loads(SRC.read_text(encoding="utf-8"))
    matches = data.get("matches_found", [])
    n = 0
    with OUT.open("w", encoding="utf-8") as f:
        for m in matches:
            d = m.get("details", {})
            row = {
                "id": m.get("url", "")[-24:],
                "url": m.get("url", ""),
                "text": "",  # TODO: paste extracted text or re-scrape
                "label": "TODO",  # TODO: 'match' or 'no_match' (human truth)
                "human_score": None,
                "legacy_score": d.get("score"),
                "note": f"{d.get('title','')} @ {d.get('company','')} · {d.get('location','')}",
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    print(f"Wrote {n} rows to {OUT}. Relabel `label` by hand, fill `text`, then rename to dataset.jsonl")


if __name__ == "__main__":
    main()
