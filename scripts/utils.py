from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Optional, Literal

import pandas as pd
import requests
import yaml
from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field, ValidationError
from rich.console import Console
from rich.logging import RichHandler
import logging

console = Console()


def setup_logging(verbosity: int = 0) -> logging.Logger:
    level = logging.INFO if verbosity <= 0 else logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console)],
    )
    return logging.getLogger("asr")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any, *, overwrite: bool = True) -> None:
    ensure_dir(path.parent)
    if path.exists() and not overwrite:
        return
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]], *, overwrite: bool = True) -> None:
    ensure_dir(path.parent)
    if path.exists() and not overwrite:
        return
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_title(title: str) -> str:
    t = (title or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s]", "", t)
    return t


def record_id_from(pmid: str, title: str) -> str:
    base = f"{str(pmid).strip()}|{normalize_title(title)}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def stable_screening_columns() -> list[str]:
    return [
        "PMID",
        "Year",
        "Journal",
        "Title",
        "IndicationBucketHint",
        "EndpointsTagged",
        "TierSuggestedFromAbstract",
        "InterventionAliveHint",
        "RandomizedHint",
        "PlaceboHint",
        "DoubleBlindHint",
        "TrialRegistryIDs",
        "NeedsRegistryCheck",
        "PublicationTypes",
        "ExcludedByPTFilter",
        "ExclusionReasonAuto",
        "Include_YN",
        "Reason_Exclude",
        "Reason_Exclude_Category",
        "NeedsFullTextReview",
        "Intervention_Class",
        "Intervention_Name",
        "Strains_or_Consortium",
        "Dose",
        "Duration_weeks",
        "Population_notes",
        "Primary_endpoint_verbatim",
        "Primary_endpoint_category",
        "Outcome_direction",
        "Effect_size",
        "Durability_timepoint",
        "TierFinal",
        "MagnitudeBarPass",
        "MagnitudeBarNotes",
        "RoB2_overall",
        "RoB2_notes",
        "RoB2_domains_json",
        "Multiplicity_flags",
        "Comments",
        "record_id",
    ]


def load_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported table format: {path}")


def save_table(df: pd.DataFrame, parquet_path: Path, csv_path: Path) -> None:
    ensure_dir(parquet_path.parent)
    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False)


def parse_only_list(value: Optional[str]) -> Optional[set[str]]:
    if not value:
        return None
    parts = [p.strip() for p in value.split(",") if p.strip()]
    return set(parts) if parts else None


def add_common_args(parser: argparse.ArgumentParser, *, table_required: bool) -> None:
    parser.add_argument("--protocol", required=True, type=Path, help="Path to protocol/protocol.yaml")
    if table_required:
        parser.add_argument("--table", required=True, type=Path, help="Path to screening table (.parquet or .csv)")
    else:
        parser.add_argument("--table", required=False, type=Path, help="Optional path to screening table")
    parser.add_argument("--limit", type=int, default=0, help="Max records to process (0=all)")
    parser.add_argument("--only", type=str, default="", help="Comma-separated record_ids to process")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing artifacts/outputs")
    parser.add_argument("--dry-run", action="store_true", help="Plan work but do not write outputs")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase logging verbosity")


def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def git_sha(root: Path) -> str:
    import subprocess

    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.DEVNULL, text=True).strip()
        return out
    except Exception:
        return "unknown"


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (set, frozenset)):
        return sorted([to_jsonable(v) for v in value])
    if isinstance(value, tuple):
        return [to_jsonable(v) for v in value]
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    return value


def make_run_manifest(step: str, args: dict[str, Any], *, root: Path) -> dict[str, Any]:
    return {
        "step": step,
        "timestamp_utc": now_utc_iso(),
        "args": to_jsonable(args),
        "git_sha": git_sha(root),
        "python": sys.version,
    }


def load_json_schema(schema_path: Path) -> dict[str, Any]:
    schema = read_json(schema_path)
    Draft202012Validator.check_schema(schema)
    return schema


def validate_json(schema: dict[str, Any], instance: Any) -> tuple[bool, list[str]]:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
    if not errors:
        return True, []
    msgs = []
    for e in errors[:25]:
        loc = ".".join(str(p) for p in e.path) if e.path else "<root>"
        msgs.append(f"{loc}: {e.message}")
    if len(errors) > 25:
        msgs.append(f"... {len(errors) - 25} more errors")
    return False, msgs


class ScreeningFlagsModel(BaseModel):
    randomized: Literal["Y", "N", "U"]
    placebo: Literal["Y", "N", "U"]
    double_blind: Literal["Y", "N", "U"]
    live_intervention: Literal["Y", "N", "U"]
    metabolic_indication: Literal["Y", "N", "U"]


class ScreeningOutputModel(BaseModel):
    include_yn: Literal["Y", "N", "U"]
    exclusion_reason_category: str
    exclusion_reason_free_text: str
    flags: ScreeningFlagsModel
    trial_registry_ids: list[str]
    confidence: float = Field(ge=0, le=1)
    needs_fulltext_review: bool
    indication_bucket_hint: str = "Unknown"
    endpoints_tagged: list[str] = []
    tier_suggested_from_abstract: str = "Unknown"
    intervention_class: str = "Unknown"


class ExtractionOutputModel(BaseModel):
    Intervention_Class: str
    Intervention_Name: str
    Strains_or_Consortium: str
    Dose: str
    Duration_weeks: float | str
    Population_notes: str
    Primary_endpoint_verbatim: str
    Primary_endpoint_category: str
    Outcome_direction: Literal["improved", "no_effect", "worsened", "mixed", "unknown"]
    Effect_size: str
    Durability_timepoint: str
    TierSuggestedFromFulltext: str = ""
    trial_registry_ids: list[str] = []

class Rob2StudyMetadataModel(BaseModel):
    reference: str
    outcome_assessed: str
    effect_of_interest: Literal["assignment", "adherence"]
    sources_used: list[
        Literal[
            "journal_article",
            "trial_protocol",
            "statistical_analysis_plan",
            "trial_registry",
            "company_registry",
            "grey_literature",
            "conference_abstract",
            "regulatory_document",
            "ethics_application",
            "grant_database",
            "personal_communication",
            "other",
        ]
    ]


class Rob2Domain1SQModel(BaseModel):
    allocation_sequence_random: Literal["Y", "PY", "PN", "N", "NI"]
    allocation_concealed: Literal["Y", "PY", "PN", "N", "NI"]
    baseline_imbalance: Literal["Y", "PY", "PN", "N", "NI"]


class Rob2Domain2SQModel(BaseModel):
    participants_aware: Literal["Y", "PY", "PN", "N", "NI"]
    carers_aware: Literal["Y", "PY", "PN", "N", "NI"]
    contextual_deviations: Literal["NA", "Y", "PY", "PN", "N", "NI"]
    deviations_affect_outcome: Literal["NA", "Y", "PY", "PN", "N", "NI"]
    deviations_balanced: Literal["NA", "Y", "PY", "PN", "N", "NI"]
    appropriate_analysis_used: Literal["Y", "PY", "PN", "N", "NI"]
    failure_impacts_result: Literal["NA", "Y", "PY", "PN", "N", "NI"]


class Rob2Domain3SQModel(BaseModel):
    data_complete: Literal["Y", "PY", "PN", "N", "NI"]
    bias_from_missing_unlikely: Literal["NA", "Y", "PY", "PN", "N", "NI"]
    missing_depends_on_true_value: Literal["NA", "Y", "PY", "PN", "N", "NI"]
    dependence_likely: Literal["NA", "Y", "PY", "PN", "N", "NI"]


class Rob2Domain4SQModel(BaseModel):
    measurement_inappropriate: Literal["Y", "PY", "PN", "N", "NI"]
    measurement_differs_between_groups: Literal["Y", "PY", "PN", "N", "NI"]
    assessors_aware: Literal["Y", "PY", "PN", "N", "NI"]
    assessment_influenced: Literal["NA", "Y", "PY", "PN", "N", "NI"]
    influence_likely: Literal["NA", "Y", "PY", "PN", "N", "NI"]


class Rob2Domain5SQModel(BaseModel):
    analysis_prespecified: Literal["Y", "PY", "PN", "N", "NI"]
    multiple_eligible_outcomes: Literal["Y", "PY", "PN", "N", "NI"]
    multiple_eligible_analyses: Literal["Y", "PY", "PN", "N", "NI"]


class Rob2Domain1Model(BaseModel):
    signaling_questions: Rob2Domain1SQModel
    judgment: Literal["Low", "Some concerns", "High"]
    rationale: str
    evidence_snippets: list[str]


class Rob2Domain2Model(BaseModel):
    effect_of_interest: Literal["assignment", "adherence"]
    signaling_questions: Rob2Domain2SQModel
    judgment: Literal["Low", "Some concerns", "High"]
    rationale: str
    evidence_snippets: list[str]


class Rob2Domain3Model(BaseModel):
    signaling_questions: Rob2Domain3SQModel
    judgment: Literal["Low", "Some concerns", "High"]
    rationale: str
    evidence_snippets: list[str]


class Rob2Domain4Model(BaseModel):
    signaling_questions: Rob2Domain4SQModel
    judgment: Literal["Low", "Some concerns", "High"]
    rationale: str
    evidence_snippets: list[str]


class Rob2Domain5Model(BaseModel):
    signaling_questions: Rob2Domain5SQModel
    judgment: Literal["Low", "Some concerns", "High"]
    rationale: str
    evidence_snippets: list[str]


class Rob2OverallModel(BaseModel):
    judgment: Literal["Low", "Some concerns", "High"]
    rationale: str
    highest_risk_domain: Literal[
        "domain_1_randomization",
        "domain_2_deviations_from_intended_interventions",
        "domain_3_missing_outcome_data",
        "domain_4_measurement_of_outcome",
        "domain_5_selection_of_reported_result",
    ]
    confidence: float = Field(ge=0, le=1)


class Rob2OutputModel(BaseModel):
    study_metadata: Rob2StudyMetadataModel
    domain_1_randomization: Rob2Domain1Model
    domain_2_deviations_from_intended_interventions: Rob2Domain2Model
    domain_3_missing_outcome_data: Rob2Domain3Model
    domain_4_measurement_of_outcome: Rob2Domain4Model
    domain_5_selection_of_reported_result: Rob2Domain5Model
    overall_risk_of_bias: Rob2OverallModel


def validate_llm_output(step: str, instance: Any) -> tuple[bool, dict[str, Any] | None, str]:
    try:
        if step == "screening":
            model = ScreeningOutputModel.model_validate(instance)
            return True, model.model_dump(), ""
        if step == "extraction":
            model = ExtractionOutputModel.model_validate(instance)
            return True, model.model_dump(), ""
        if step == "rob2":
            model = Rob2OutputModel.model_validate(instance)
            return True, model.model_dump(), ""
        return False, None, f"Unknown step for validation: {step}"
    except ValidationError as e:
        return False, None, str(e)


@dataclasses.dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    model: str
    temperature: float
    base_url: str
    timeout_s: float


def openai_client() -> OpenAIConfig:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini").strip()
    temperature = float(os.environ.get("OPENAI_TEMPERATURE", "0.2"))
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com").strip() or "https://api.openai.com"
    timeout_s = float(os.environ.get("OPENAI_TIMEOUT_S", "120"))
    return OpenAIConfig(api_key=api_key, model=model, temperature=temperature, base_url=base_url, timeout_s=timeout_s)


def _openai_headers(cfg: OpenAIConfig) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }


def call_llm_json(
    *,
    step: str,
    record_id: str,
    input_text: str,
    prompt_path: Path,
    schema_path: Path,
    artifacts_dir: Path,
    overwrite: bool,
    logger: logging.Logger,
    input_identifiers: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    cfg = openai_client()
    ensure_dir(artifacts_dir)
    req_path = artifacts_dir / "request.json"
    resp_path = artifacts_dir / "response.json"
    parsed_path = artifacts_dir / "parsed.json"

    if parsed_path.exists() and not overwrite:
        return read_json(parsed_path)

    if not cfg.api_key:
        raise RuntimeError("OPENAI_API_KEY not set; cannot run LLM steps.")

    schema = load_json_schema(schema_path)
    prompt = prompt_path.read_text(encoding="utf-8")

    def read_optional(path: Path) -> str:
        try:
            if path.exists():
                return path.read_text(encoding="utf-8").strip()
        except Exception:
            return ""
        return ""

    protocol_text = read_optional(Path("protocol/protocol.yaml"))
    decision_rules_text = read_optional(Path("docs/decision_rules.md"))
    endpoint_taxonomy_text = read_optional(Path("docs/endpoint_taxonomy.md"))
    rob2_text = read_optional(Path("ROB_protocols/ROB2.0.txt"))
    rob2_json_template_text = read_optional(Path("ROB_protocols/ROB2.0_json.txt"))

    extra_context_parts: list[str] = []
    if protocol_text:
        extra_context_parts.append("=== protocol/protocol.yaml ===\n" + protocol_text)
    if decision_rules_text:
        extra_context_parts.append("=== docs/decision_rules.md ===\n" + decision_rules_text)
    if step == "extraction" and endpoint_taxonomy_text:
        extra_context_parts.append("=== docs/endpoint_taxonomy.md ===\n" + endpoint_taxonomy_text)
    if step == "rob2":
        if rob2_text:
            extra_context_parts.append("=== ROB_protocols/ROB2.0.txt ===\n" + rob2_text)
        if rob2_json_template_text:
            extra_context_parts.append("=== ROB_protocols/ROB2.0_json.txt ===\n" + rob2_json_template_text)
    extra_context = "\n\n".join([p for p in extra_context_parts if p]).strip()

    system_text = (
        "You are a careful, conservative systematic review assistant. "
        "Return strictly valid JSON. Do not include markdown or explanations. "
        "Never hallucinate; if information is not explicitly present, use Unknown / U / NI as appropriate."
    )

    payload_responses = {
        "model": cfg.model,
        "temperature": cfg.temperature,
        "input": [
            {"role": "system", "content": system_text},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *([{"type": "text", "text": "\n\n=== CONTEXT ===\n" + extra_context}] if extra_context else []),
                    {"type": "text", "text": f"\n\n=== INPUT (record_id={record_id}) ===\n{input_text}\n"},
                ],
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": f"{step}_schema", "schema": schema, "strict": True},
        },
    }

    payload_chat = {
        "model": cfg.model,
        "temperature": cfg.temperature,
        "messages": [
            {"role": "system", "content": system_text},
            {
                "role": "user",
                "content": prompt
                + ("\n\n=== CONTEXT ===\n" + extra_context if extra_context else "")
                + "\n\n=== INPUT ===\n"
                + input_text
                + "\n\nReturn ONLY valid JSON matching this schema:\n"
                + json.dumps(schema, ensure_ascii=False),
            },
        ],
        "response_format": {"type": "json_object"},
    }

    def do_request_responses(payload: dict[str, Any]) -> dict[str, Any]:
        url = cfg.base_url.rstrip("/") + "/v1/responses"
        r = requests.post(url, headers=_openai_headers(cfg), json=payload, timeout=cfg.timeout_s)
        r.raise_for_status()
        return r.json()

    def do_request_chat(payload: dict[str, Any]) -> dict[str, Any]:
        url = cfg.base_url.rstrip("/") + "/v1/chat/completions"
        r = requests.post(url, headers=_openai_headers(cfg), json=payload, timeout=cfg.timeout_s)
        r.raise_for_status()
        return r.json()

    def do_request(payload: dict[str, Any], payload_chat_attempt: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any]]:
        try:
            return "responses", do_request_responses(payload), payload
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            # Fallback for older accounts/models that don't support Responses API.
            if status in {400, 404, 410}:
                return "chat_completions", do_request_chat(payload_chat_attempt), payload_chat_attempt
            raise

    def extract_json_from_responses(resp: dict[str, Any]) -> Any:
        # Responses API returns structured output inside output_text / output content.
        # Try common shapes; fall back to parsing aggregated text.
        if "output" in resp:
            for item in resp.get("output", []):
                for c in item.get("content", []) or []:
                    if c.get("type") in ("output_json", "json"):
                        return c.get("json")
        text = resp.get("output_text") or ""
        if not text and "output" in resp:
            chunks = []
            for item in resp.get("output", []):
                for c in item.get("content", []) or []:
                    if c.get("type") in ("output_text", "text"):
                        chunks.append(c.get("text", ""))
            text = "\n".join(chunks).strip()
        return json.loads(text)

    def extract_json_from_chat(resp: dict[str, Any]) -> Any:
        content = (
            resp.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return json.loads(content)

    last_err: Optional[str] = None
    for attempt in range(2):
        payload = payload_responses
        payload_chat_attempt = dict(payload_chat)
        if attempt == 1 and last_err:
            payload = dict(payload_responses)
            payload["input"] = list(payload_responses["input"])
            payload["input"].append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Your prior output did not validate. Fix and return ONLY valid JSON. Errors:\n{last_err}",
                        }
                    ],
                }
            )
            payload_chat_attempt = dict(payload_chat)
            payload_chat_attempt["messages"] = list(payload_chat["messages"]) + [
                {"role": "user", "content": f"Your prior output did not validate. Fix and return ONLY valid JSON. Errors:\n{last_err}"}
            ]

        api_used, resp, payload_used = do_request(payload, payload_chat_attempt)
        req_meta = {
            "timestamp_utc": now_utc_iso(),
            "step": step,
            "record_id": record_id,
            "input_identifiers": input_identifiers or {},
            "model": cfg.model,
            "temperature": cfg.temperature,
            "base_url": cfg.base_url,
            "prompt_path": str(prompt_path),
            "schema_path": str(schema_path),
            "prompt_text": prompt,
        }
        write_json(req_path, {"api": api_used, "meta": req_meta, "payload": payload_used}, overwrite=True)
        write_json(resp_path, {"api": api_used, "meta": req_meta, "response": resp}, overwrite=True)

        if api_used == "responses":
            parsed = extract_json_from_responses(resp)
        else:
            parsed = extract_json_from_chat(resp)

        ok, cleaned, err = validate_llm_output(step, parsed)
        if ok and cleaned is not None:
            write_json(parsed_path, cleaned, overwrite=True)
            return cleaned
        last_err = err
        logger.warning("Pydantic validation failed for %s attempt %d: %s", record_id, attempt + 1, last_err)

    raise ValueError(f"LLM output did not validate for record_id={record_id}: {last_err}")


def coerce_bool_hint(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "unknown"
    v = str(value).strip().lower()
    if v in {"true", "t", "yes", "y", "1"}:
        return "true"
    if v in {"false", "f", "no", "n", "0"}:
        return "false"
    return "unknown"


def coerce_list_to_str(values: Any, *, sep: str = ",") -> str:
    if values is None:
        return ""
    if isinstance(values, str):
        return values
    if isinstance(values, list):
        return sep.join(str(v).strip() for v in values if str(v).strip())
    return str(values)


def limit_records(df: pd.DataFrame, *, only: Optional[set[str]], limit: int) -> pd.DataFrame:
    out = df
    if only:
        out = out[out["record_id"].astype(str).isin(only)]
    if limit and limit > 0:
        out = out.head(limit)
    return out
