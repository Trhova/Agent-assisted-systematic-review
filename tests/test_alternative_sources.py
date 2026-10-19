from types import SimpleNamespace

import pytest

from scripts.acquisition import AcquisitionError
from scripts.discover_sources import discover_pdf


@pytest.mark.parametrize(
    "alternate",
    ["https://other.example/trial.pdf", "https://blocked.example/trial.pdf"],
)
def test_alternate_search_only_after_failed_candidate_and_never_retries_url(
    tmp_path, monkeypatch, alternate
):
    first = "https://blocked.example/trial.pdf"
    searches = []
    downloads = []

    def discover(record, folder, model=None, failed_urls=()):
        searches.append(list(failed_urls))
        return [alternate] if failed_urls else [first]

    class Fetcher:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, url):
            downloads.append(url)
            if url == first:
                raise AcquisitionError("HTTP 403")
            return b"%PDF fixture", {"url": url}

    monkeypatch.setattr("scripts.web_source_discovery.discover", discover)
    monkeypatch.setattr("scripts.discover_sources.PublicFetcher", Fetcher)
    monkeypatch.setattr(
        "scripts.discover_sources.front_page_text", lambda _: "DOI: 10.1234/trial"
    )
    monkeypatch.setattr(
        "scripts.discover_sources.importlib.import_module",
        lambda _: SimpleNamespace(
            extract_pdf_text=lambda _: {
                "pages": [
                    {"page": 1, "text": "DOI: 10.1234/trial " + "Article body " * 100}
                ]
            }
        ),
    )
    result = discover_pdf(
        {"id": "1", "doi": "10.1234/trial"},
        tmp_path,
        providers=False,
        web_fallback=True,
    )
    assert searches == [[], [first]]
    assert downloads.count(first) == 1
    if alternate == first:
        assert result is None
    else:
        assert result["pdf_relative_path"].startswith("alternate_candidate_downloads/")
        assert (tmp_path / result["pdf_relative_path"]).exists()
        assert "alternate-source" in result["acquisition_method"]


def test_empty_initial_discovery_stops_without_speculative_repeat(
    tmp_path, monkeypatch
):
    calls = []

    def discover(*args, **kwargs):
        calls.append(1)
        return []

    monkeypatch.setattr("scripts.web_source_discovery.discover", discover)
    assert (
        discover_pdf({"id": "x"}, tmp_path, providers=False, web_fallback=True) is None
    )
    assert len(calls) == 1


def test_source_search_preserves_explicit_model_selection(tmp_path, monkeypatch):
    from scripts.source_access import indexed_pdf

    seen = {}

    def discover(*args, **kwargs):
        seen.update(kwargs)
        return None

    monkeypatch.setattr("scripts.source_access.discover_pdf", discover)
    indexed_pdf({"id": "x"}, tmp_path, tmp_path / "source", model="explicit-model")
    assert seen["model"] == "explicit-model"
