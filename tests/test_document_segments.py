import json

from scripts.document_segments import segments, triage
from scripts.model_backend import digest


def test_segments_cover_every_character_with_exact_offsets():
    text = "An example paragraph.\n" * 100
    chunks = list(segments(text, size=300, overlap=30))
    covered = set()
    for c in chunks:
        assert text[c["start"] : c["end"]] == c["text"]
        assert c["sha256"] == digest(c["text"])
        covered.update(range(c["start"], c["end"]))
    assert len(covered) == len(text)


def test_triage_resumes_and_keeps_unsupported_evidence_unresolved(tmp_path):
    text = "Trial title\nRandomized humans received probiotics." + " x" * 40000
    doc = {"text": text, "sha256": digest(text)}
    calls = []

    def call(prompt, schema, *args, **kwargs):
        calls.append(prompt)
        return {
            "candidates": [
                {
                    "title": "Invented trial",
                    "evidence": "Invented numbers",
                    "reason": "fixture",
                    "publication_form": "unclear",
                }
            ]
        }

    r = triage(doc, "fixture", tmp_path, max_new=1, call=call)
    assert r["completed_segments"] == 1 and r["status"] == "incomplete"
    assert not r["candidates"] and r["unsupported_candidates"] == 1
    r = triage(doc, "fixture", tmp_path, max_new=1, call=call)
    assert len(calls) == 4 and r["completed_segments"] == 2
    assert json.loads(
        (tmp_path / next(tmp_path.iterdir()).name / "manifest.json").read_text()
    )["source_characters"] == len(text)
