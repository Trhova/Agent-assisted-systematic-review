import threading

import pytest

from scripts.source_queue import acquire_ordered


def test_bounded_prefetch_retains_order_and_reports_errors():
    barrier = threading.Barrier(3, timeout=5)
    calls = []
    lock = threading.Lock()

    def fetch(record):
        with lock:
            calls.append(record["id"])
        if int(record["id"]) < 3:
            barrier.wait()
        if record["id"] == "1":
            raise RuntimeError("source unavailable")
        return {"text": record["id"]}

    rows = list(acquire_ordered([{"id": str(i)} for i in range(5)], fetch))
    assert [r[0]["id"] for r in rows] == [str(i) for i in range(5)]
    assert len(calls) == len(set(calls)) == 5
    assert rows[1][1] is None and isinstance(rows[1][2], RuntimeError)
    assert rows[4][1] == {"text": "4"}


def test_duplicate_report_queue_is_rejected_before_acquisition():
    with pytest.raises(ValueError, match="race"):
        list(
            acquire_ordered([{"id": "a"}, {"id": "a"}], lambda r: pytest.fail("called"))
        )


def test_newly_resolved_reports_are_consumed_after_last_original_record():
    records = [{"id": "collection"}]
    queue = acquire_ordered(records, lambda r: r["id"])
    assert next(queue)[1] == "collection"
    records.append({"id": "new-trial"})
    assert next(queue)[1] == "new-trial"
    with pytest.raises(StopIteration):
        next(queue)
