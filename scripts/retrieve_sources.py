"""Optional prefetch of independently screened candidates, without reference access."""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from scripts.autonomous_review import fulltext


def prefetch(work):
    records = {
        r["id"]: r for r in json.loads((work / "search.json").read_text())["records"]
    }
    decisions = json.loads((work / "screening.json").read_text())
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fulltext, records[d["id"]], work): d["id"]
            for d in decisions
            if d["decision"] != "exclude"
        }
        for future in as_completed(futures):
            rid = futures[future]
            try:
                doc = future.result()
                print(rid, "available" if doc else "unavailable", flush=True)
            except Exception as error:
                print(rid, "retrieval_error", str(error), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--run", type=Path, required=True)
    a = p.parse_args()
    prefetch(a.run)
