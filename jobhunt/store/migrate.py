"""Import the legacy memory.json into the SQLite store.

The legacy format stored predictions as:
  {"url": ..., "details": {"score", "score_detail": {stack,role,location,contract},
   "title", "company", "location", "contract_type", "stack_match", "summary"}}

We map score_detail → the new typed breakdown (without gaps, since the legacy
data has none) so old matches show up in the new dashboard.
"""
from __future__ import annotations

import json
from pathlib import Path

from jobhunt.store import Job, Store

_MAX = {"stack": 40, "role": 20, "location": 25, "contract": 15}


def import_memory(memory_path: str | Path = "memory.json", db_path: str | Path = "jobhunt.db") -> int:
    src = Path(memory_path)
    if not src.exists():
        print(f"No legacy memory at {src}")
        return 0
    data = json.loads(src.read_text(encoding="utf-8"))
    store = Store(db_path)
    n = 0
    for m in data.get("matches_found", []):
        d = m.get("details", {})
        detail = d.get("score_detail", {}) or {}
        breakdown = {
            k: {
                "score": int(detail.get(k, 0) or 0),
                "max": mx,
                "matched": d.get("stack_match", []) if k == "stack" else [],
                "gaps": [],
            }
            for k, mx in _MAX.items()
        }
        job = Job(
            url=m.get("url", ""),
            title=d.get("title", "Sans titre"),
            company=d.get("company", "Inconnue"),
            location=d.get("location", ""),
            contract=d.get("contract_type", ""),
            score=int(d.get("score", 0) or 0),
            breakdown=breakdown,
            summary=d.get("summary", ""),
            source=(m.get("url", "").split("/")[2] if "/" in m.get("url", "") else ""),
        )
        if job.url:
            store.upsert_job(job)
            n += 1
    # carry over visited URLs and searches so a resumed run won't re-crawl
    for url in data.get("visited_urls", []):
        store.mark_visited(url)
    for q in data.get("searches_done", []):
        store.mark_search(q)
    store.close()
    print(f"Imported {n} matches + {len(data.get('visited_urls', []))} visited URLs into {db_path}")
    return n


if __name__ == "__main__":
    import sys

    import_memory(*(sys.argv[1:3] or []))
