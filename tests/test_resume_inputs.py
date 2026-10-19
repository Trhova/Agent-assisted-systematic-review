import pytest

from scripts.model_backend import atomic_json
from scripts.resume_inputs import prepare


def test_copy_retains_raw_metadata_and_excludes_answers(tmp_path):
    source, dest = tmp_path / "source", tmp_path / "dest"
    atomic_json(source / "status.json", {"status": "incomplete"})
    atomic_json(source / "search.json", {"query": "frozen", "records": []})
    atomic_json(source / "search_raw.json", [{"fullTextUrlList": "source links"}])
    atomic_json(source / "accepted.json", {"gold": "not input"})
    atomic_json(source / "benchmark_comparison.json", {"reference": "not input"})
    atomic_json(source / "rob2_drafts/model/hash/parsed.json", {"cached": True})
    atomic_json(source / "rob2_drafts/compiled.json", {"compiled": True})
    atomic_json(source / "rob2_draft.json", {"compiled": True})
    prepare(source, dest)
    assert (dest / "search_raw.json").read_bytes() == (
        source / "search_raw.json"
    ).read_bytes()
    assert not (dest / "accepted.json").exists()
    assert not (dest / "benchmark_comparison.json").exists()
    assert (dest / "rob2_drafts/model/hash/parsed.json").exists()
    assert not (dest / "rob2_drafts/compiled.json").exists()
    assert not (dest / "rob2_draft.json").exists()
    with pytest.raises(ValueError, match="empty"):
        prepare(source, dest)


def test_missing_provenance_requires_exact_origin(tmp_path):
    source, origin, dest = [tmp_path / x for x in ["source", "origin", "dest"]]
    atomic_json(source / "status.json", {"status": "incomplete"})
    atomic_json(source / "search.json", {"query": "a", "records": [1]})
    with pytest.raises(ValueError, match="provenance"):
        prepare(source, dest)
    atomic_json(origin / "search.json", {"query": "a", "records": [2]})
    atomic_json(origin / "search_raw.json", [])
    with pytest.raises(ValueError, match="exact frozen"):
        prepare(source, dest, origin)
    atomic_json(origin / "search.json", {"query": "a", "records": [1]})
    prepare(source, dest, origin)
    atomic_json(source / "status.json", {"status": "running"})
    with pytest.raises(ValueError, match="running"):
        prepare(source, tmp_path / "new")
