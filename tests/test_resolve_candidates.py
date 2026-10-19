import json

from scripts.resolve_candidates import resolve_candidates


def test_candidate_resolution_rejects_similar_but_different_title(
    tmp_path, monkeypatch
):
    class Fetcher:
        def __init__(self, *a, **k):
            pass

        def get(self, url):
            return json.dumps(
                {
                    "resultList": {
                        "result": [
                            {"id": "1", "source": "MED", "title": "Different trial"}
                        ]
                    }
                }
            ).encode(), {}

    monkeypatch.setattr("scripts.resolve_candidates.PublicFetcher", Fetcher)
    result = resolve_candidates(
        [{"title": "Original trial title", "occurrences": []}], tmp_path
    )
    assert not result["records"] and result["status"] == "incomplete"


def test_resolved_title_keeps_date_for_original_eligibility_screen(
    tmp_path, monkeypatch
):
    class Fetcher:
        def __init__(self, *a, **k):
            pass

        def get(self, url):
            return json.dumps(
                {
                    "resultList": {
                        "result": [
                            {
                                "id": "1",
                                "source": "MED",
                                "title": "Original trial title.",
                                "firstPublicationDate": "2020-01-01",
                            }
                        ]
                    }
                }
            ).encode(), {}

    monkeypatch.setattr("scripts.resolve_candidates.PublicFetcher", Fetcher)
    result = resolve_candidates(
        [{"title": "Original trial title", "occurrences": []}], tmp_path
    )
    assert result["records"][0]["date"] == "2020-01-01"
    assert result["status"] == "resolved"
