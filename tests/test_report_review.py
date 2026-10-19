import csv

import pytest

from scripts.model_backend import atomic_json
from scripts.report_review import export


def test_report_preserves_unavailable_sources_and_never_implies_pool(tmp_path):
    work = tmp_path / "run"
    out = tmp_path / "report"
    atomic_json(work / "status.json", {"status": "incomplete"})
    atomic_json(
        work / "search.json", {"records": [{"id": "1", "title": "=Untrusted title"}]}
    )
    atomic_json(
        work / "screening.json",
        [{"id": "1", "decision": "unclear", "reason": "No abstract"}],
    )
    atomic_json(work / "extractions.json", [{"id": "1", "status": "missing_fulltext"}])
    atomic_json(
        work / "sources" / "1" / "unavailable.json", {"errors": ["Source inaccessible"]}
    )
    atomic_json(
        work / "sources" / "1" / "web_discovery.json",
        {"reason": "No public report located"},
    )
    export(work, out)
    rows = list(csv.DictReader((out / "decisions.csv").open()))
    assert rows[0]["title"].startswith("'=")
    assert rows[0]["fulltext_status"] == "missing_fulltext"
    assert rows[0]["retrieval_details"] == "Source inaccessible"
    assert rows[0]["public_copy_search"] == "No public report located"
    assert "No valid pooled estimate" in (out / "review.md").read_text()
    atomic_json(work / "status.json", {"status": "running"})
    with pytest.raises(ValueError, match="finished"):
        export(work, out)
