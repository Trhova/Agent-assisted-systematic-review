"""Bounded source prefetch; extraction consumes each report in fixed input order."""

from concurrent.futures import ThreadPoolExecutor


def acquire_ordered(records, fetch, workers=3):
    if workers < 1 or workers > 4:
        raise ValueError("Source workers must be between one and four")
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("Repeated report IDs would race source acquisition")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        pending = {}
        for i, record in enumerate(records):
            # At most workers unresolved source operations; no unbounded queue.
            while len(pending) < workers:
                nxt = i + len(pending)
                if nxt >= len(records):
                    break
                pending[nxt] = executor.submit(fetch, records[nxt])
            future = pending.pop(i)
            try:
                yield record, future.result(), None
            except Exception as error:
                yield record, None, error
