import json
from types import SimpleNamespace

import pytest

from scripts.bibliographic_search import search


def page(ids, cursor):
    return SimpleNamespace(
        json=lambda: {
            "hitCount": 2,
            "nextCursorMark": cursor,
            "resultList": {"result": [{"id": i, "source": "MED"} for i in ids]},
        }
    )


def test_interrupted_search_resumes_last_completed_page(tmp_path):
    calls = []

    def fetch(url, params):
        calls.append(params["cursorMark"])
        if len(calls) == 2:
            raise RuntimeError("connection lost")
        return page(["1"], "next")

    with pytest.raises(RuntimeError):
        search({"query": "frozen"}, tmp_path, fetch)
    assert not (tmp_path / "search.json").exists()

    def resume(url, params):
        assert params["cursorMark"] == "next"
        return page(["2"], "next")

    result = search({"query": "frozen"}, tmp_path, resume)
    assert [r["id"] for r in result["records"]] == ["1", "2"]
    assert len(json.loads((tmp_path / "search_raw.json").read_text())) == 2
    with pytest.raises(ValueError, match="query differs"):
        search({"query": "changed"}, tmp_path, None)


def test_cursor_cycle_and_budget_fail_closed(tmp_path):
    responses = iter([page(["1"], "next"), page(["2"], "*")])
    with pytest.raises(ValueError, match="cycle"):
        search({"query": "a"}, tmp_path, lambda *a, **k: next(responses))
    assert not (tmp_path / "search.json").exists()
    other = tmp_path / "bounded"
    with pytest.raises(ValueError, match="budget"):
        search({"query": "a"}, other, lambda *a, **k: page(["1"], "next"), max_pages=1)
    assert (other / "search_progress.json").exists()


def test_cached_search_without_raw_metadata_is_not_silently_accepted(tmp_path):
    (tmp_path / "search.json").write_text('{"query":"frozen","records":[]}')
    with pytest.raises(ValueError, match="raw bibliographic provenance"):
        search({"query": "frozen"}, tmp_path, None)


def test_linked_integrity_notice_is_flagged():
    from scripts.autonomous_review import publication_integrity_flags

    r = {
        "publication_types": ["Randomized Controlled Trial"],
        "related_notices": [
            {"type": "Expression of concern in", "id": "123"},
            {"type": "Erratum in", "id": "456"},
        ],
    }
    assert publication_integrity_flags(r) == ["Linked Expression of concern in: 123"]


def test_unknown_query_field_is_rejected_before_search(tmp_path):
    import pytest

    from scripts.bibliographic_search import search

    class Response:
        def json(self):
            return {"searchTermList": {"searchTerms": [{"term": "TITLE_ABS"}]}}

    with pytest.raises(ValueError, match="MESH"):
        search(
            {"query": "MESH:Diabetes", "validate_query_fields": True},
            tmp_path,
            lambda *a, **kw: Response(),
        )
