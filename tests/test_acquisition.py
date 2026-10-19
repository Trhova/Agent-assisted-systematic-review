import hashlib

import pytest

from scripts.acquisition import AcquisitionError, PublicFetcher, public_url
from scripts.discover_sources import PDFLinks, source_identity
from scripts.model_backend import atomic_json, digest


def test_source_identity_does_not_accept_reference_on_later_pages():
    record = {
        "doi": "10.1234/target",
        "title": "A sufficiently long randomized trial title",
    }
    assert not source_identity(record, "Different trial report")["verified"]
    assert source_identity(record, "DOI: 10.1234/target")["verified"]
    assert source_identity(record, "A sufficiently long randomized\ntrial title")[
        "verified"
    ]


def test_landing_metadata_attribute_order_and_relative_url():
    p = PDFLinks()
    p.feed(
        '<meta content="/trial.pdf" name="citation_pdf_url"><link href="/second.pdf" type="application/pdf">'
    )
    assert p.links == ["/trial.pdf", "/second.pdf"]


def test_negative_cache_prevents_repeated_network(tmp_path, monkeypatch):
    url = "https://example.org/missing"
    atomic_json(
        tmp_path / digest(url) / "response.json",
        {"status": "failed", "retry_after_epoch": 10**12, "error": "HTTP 403"},
    )
    monkeypatch.setattr(
        "scripts.acquisition.requests.get",
        lambda *a, **k: pytest.fail("network called"),
    )
    with pytest.raises(AcquisitionError, match="Cached"):
        PublicFetcher(tmp_path).get(url)


def test_positive_cache_validates_checksum(tmp_path):
    url = "https://example.org/source"
    folder = tmp_path / digest(url)
    atomic_json(
        folder / "response.json",
        {"status": "success", "sha256": hashlib.sha256(b"abc").hexdigest()},
    )
    (folder / "body").write_bytes(b"abc")
    assert PublicFetcher(tmp_path, max_requests=0).get(url)[0] == b"abc"
    (folder / "body").write_bytes(b"changed")
    with pytest.raises(AcquisitionError, match="checksum"):
        PublicFetcher(tmp_path).get(url)


def test_public_destination_guard():
    for url in [
        "file:///etc/passwd",
        "http://127.0.0.1/",
        "http://user:secret@example.org/",
    ]:
        with pytest.raises(AcquisitionError):
            public_url(url)


def test_host_cooldown_applies_to_different_record_urls(tmp_path, monkeypatch):
    hosts = tmp_path / "shared_hosts"
    atomic_json(
        hosts / (digest("example.org") + ".json"), {"retry_after_epoch": 10**12}
    )
    monkeypatch.setattr(
        "scripts.acquisition.requests.get",
        lambda *a, **k: pytest.fail("rate-limited host contacted"),
    )
    with pytest.raises(AcquisitionError, match="cooldown"):
        PublicFetcher(tmp_path / "record_b", host_cache=hosts).get(
            "https://example.org/other"
        )


def test_download_byte_limit_never_caches_partial_success(tmp_path, monkeypatch):
    class Response:
        status_code = 200
        is_redirect = False
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def raise_for_status(self):
            pass

        def iter_content(self, *args):
            yield b"0123456789abcdef"

    monkeypatch.setattr("scripts.acquisition.public_url", lambda u: u)
    monkeypatch.setattr("scripts.acquisition.requests.get", lambda *a, **k: Response())
    with pytest.raises(AcquisitionError, match="budget"):
        PublicFetcher(tmp_path, max_bytes=10).get("https://example.org/large")
    folder = tmp_path / digest("https://example.org/large")
    assert not (folder / "body").exists()
    import json

    assert json.loads((folder / "response.json").read_text())["status"] == "failed"


def test_extraction_and_web_discovery_model_caches_are_separate():
    from scripts.model_backend import request_identity

    plain = request_identity("same prompt", {})
    web = request_identity("same prompt", {}, allow_web=True)
    assert digest(plain) != digest(web)
    assert "allow_web" not in plain and web["allow_web"] is True


def test_doi_identity_rejects_prefix_collision_but_allows_pdf_line_breaks():
    record = {"doi": "10.1234/trial", "title": ""}
    assert not source_identity(record, "DOI 10.1234/trial-followup")["verified"]
    assert not source_identity(record, "DOI 10.1234/trial.part2")["verified"]
    assert source_identity(record, "DOI: 10.1234/\ntrial\nAuthors")["verified"]
    assert source_identity(record, "DOI: 10.1234/trial. More text")["verified"]


def test_wrong_pdf_identity_is_rejected_before_full_document_parsing(
    tmp_path, monkeypatch
):
    from scripts.discover_sources import discover_pdf

    class Fetcher:
        def get(self, url):
            return b"%PDF wrong article", {"url": url}

    monkeypatch.setattr(
        "scripts.discover_sources.front_page_text", lambda _: "Different paper"
    )
    monkeypatch.setattr(
        "scripts.discover_sources.importlib.import_module",
        lambda _: pytest.fail("Wrong document fully parsed"),
    )
    assert (
        discover_pdf(
            {"id": "x", "doi": "10.1234/right"},
            tmp_path,
            ["https://example.org/wrong.pdf"],
            fetcher=Fetcher(),
            providers=False,
        )
        is None
    )


def test_transient_http_failures_back_off_without_day_long_access_block():
    from scripts.acquisition import failure_retry_epoch

    assert failure_retry_epoch({"http_status": 500, "failure_count": 1}, 1000) == 1060
    assert failure_retry_epoch({"http_status": 503, "failure_count": 3}, 1000) == 1240
    assert failure_retry_epoch({"http_status": 403}, 1000) == 87400
    assert (
        failure_retry_epoch(
            {"http_status": 429, "server_retry_after_epoch": 1600}, 1000
        )
        == 1600
    )
    assert (
        failure_retry_epoch(
            {
                "error": "Host rate limit cooldown active",
                "server_retry_after_epoch": 1800,
            },
            1000,
        )
        == 1800
    )


def test_indexed_source_urls_retain_only_public_metadata_links(tmp_path):
    from scripts.source_access import indexed_source_urls

    atomic_json(
        tmp_path / "search_raw.json",
        [
            {
                "resultList": {
                    "result": [
                        {
                            "id": "1",
                            "source": "MED",
                            "fullTextUrlList": {
                                "fullTextUrl": [
                                    {
                                        "availabilityCode": "OA",
                                        "url": "https://example.org/open",
                                    },
                                    {
                                        "availabilityCode": "S",
                                        "url": "https://example.org/subscription",
                                    },
                                ]
                            },
                        },
                        {
                            "id": "1",
                            "source": "PMC",
                            "fullTextUrlList": {
                                "fullTextUrl": [
                                    {
                                        "availabilityCode": "OA",
                                        "url": "https://example.org/wrong",
                                    }
                                ]
                            },
                        },
                    ]
                }
            }
        ],
    )
    assert indexed_source_urls({"id": "1"}, tmp_path) == ["https://example.org/open"]
    atomic_json(tmp_path / "search_raw.json", [{"resultList": {"result": []}}])
    assert indexed_source_urls({"id": "1"}, tmp_path) == []


def test_cache_only_replay_does_not_retry_expired_or_new_urls(tmp_path, monkeypatch):
    monkeypatch.setenv('ASR_ACQUISITION_CACHE_ONLY', '1')
    monkeypatch.setattr('scripts.acquisition.requests.get',
                        lambda *a, **k: pytest.fail('network called'))
    url = 'https://example.org/expired'
    atomic_json(tmp_path / digest(url) / 'response.json',
                {'status': 'failed', 'retry_after_epoch': 0, 'error': 'HTTP 500'})
    for target in [url, 'https://example.org/new']:
        with pytest.raises(AcquisitionError, match='Cache-only'):
            PublicFetcher(tmp_path).get(target)
    body = b'preserved original'
    folder = tmp_path / digest('https://example.org/good')
    atomic_json(folder / 'response.json',
                {'status': 'success', 'sha256': hashlib.sha256(body).hexdigest()})
    (folder / 'body').write_bytes(body)
    assert PublicFetcher(tmp_path).get('https://example.org/good')[0] == body
