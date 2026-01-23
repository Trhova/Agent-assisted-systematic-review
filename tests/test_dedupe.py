def test_dedupe_by_pmid_preserves_first():
    records = [{"pmid": "1", "x": 1}, {"pmid": "1", "x": 2}, {"pmid": "2", "x": 3}]
    by_pmid = {}
    for r in records:
        if r["pmid"] and r["pmid"] not in by_pmid:
            by_pmid[r["pmid"]] = r
    deduped = list(by_pmid.values())
    assert [r["pmid"] for r in deduped] == ["1", "2"]
    assert deduped[0]["x"] == 1

