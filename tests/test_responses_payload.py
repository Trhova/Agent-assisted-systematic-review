import json
import logging
from pathlib import Path

from scripts import utils


def test_responses_wire_format_and_strict_schema(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    result = {
        "include_yn": "U",
        "exclusion_reason_category": "",
        "exclusion_reason_free_text": "",
        "flags": dict.fromkeys(
            [
                "randomized",
                "placebo",
                "double_blind",
                "live_intervention",
                "metabolic_indication",
            ],
            "U",
        ),
        "trial_registry_ids": [],
        "confidence": 0.5,
        "needs_fulltext_review": True,
    }
    captured = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "output": [
                    {"content": [{"type": "output_text", "text": json.dumps(result)}]}
                ]
            }

    def post(url, **kwargs):
        captured.append((url, kwargs["json"]))
        return Response()

    monkeypatch.setattr(utils.requests, "post", post)
    utils.call_llm_json(
        step="screening",
        record_id="fixture",
        input_text="No abstract",
        prompt_path=Path("protocol/prompts/screen_abstract.md"),
        schema_path=Path("protocol/schemas/screening.schema.json"),
        artifacts_dir=tmp_path,
        overwrite=False,
        logger=logging.getLogger(),
    )
    url, payload = captured[0]
    assert url.endswith("/v1/responses") and "response_format" not in payload
    assert all(c["type"] == "input_text" for c in payload["input"][1]["content"])
    schema = payload["text"]["format"]["schema"]
    assert set(schema["required"]) == set(schema["properties"])
