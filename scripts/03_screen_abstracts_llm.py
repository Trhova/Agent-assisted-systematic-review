from __future__ import annotations

import argparse
import re
from pathlib import Path

from scripts.utils import (
    add_common_args,
    call_llm_json,
    coerce_bool_hint,
    ensure_dir,
    load_table,
    make_run_manifest,
    parse_only_list,
    setup_logging,
    stable_screening_columns,
    write_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM abstract screening with structured outputs.")
    add_common_args(parser, table_required=True)
    args = parser.parse_args()

    logger = setup_logging(args.verbose)
    root = Path(".").resolve()
    only = parse_only_list(args.only)

    if args.dry_run and not args.table.exists():
        logger.info("Dry run: table not found (%s); nothing to do.", args.table)
        return

    df = load_table(args.table)
    cols = stable_screening_columns()
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]

    todo = df.copy()
    if only:
        todo = todo[todo["record_id"].astype(str).isin(only)]

    unscreened = todo[(todo["Include_YN"].isna()) | (todo["Include_YN"].astype(str).str.strip() == "")]
    if len(unscreened) > 0:
        todo = unscreened

    if args.limit and args.limit > 0:
        todo = todo.head(args.limit)

    schema_path = Path("protocol/schemas/screening.schema.json")
    prompt_path = Path("protocol/prompts/screen_abstract.md")
    base_dir = Path("data/intermediate/llm/screening")
    ensure_dir(base_dir)

    abstract_by_record: dict[str, str] = {}
    raw_path = Path("data/raw/pubmed_records.jsonl")
    if raw_path.exists():
        import json

        with raw_path.open("r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                rid = str(r.get("record_id") or "")
                if rid:
                    abstract_by_record[rid] = str(r.get("abstract") or "")

    processed = 0
    failures = 0
    for _, row in todo.iterrows():
        record_id = str(row["record_id"])
        pmid = str(row["PMID"])

        if args.dry_run:
            logger.info("Dry run: would screen %s (%s)", record_id, pmid)
            continue

        artifacts_dir = base_dir / record_id
        try:
            title = str(row["Title"] or "")
            abstract = abstract_by_record.get(record_id, "")
            input_text = f"PMID: {pmid}\nTitle: {title}\n\nAbstract:\n{abstract}".strip()
            parsed = call_llm_json(
                step="screening",
                record_id=record_id,
                input_text=input_text,
                prompt_path=prompt_path,
                schema_path=schema_path,
                artifacts_dir=artifacts_dir,
                overwrite=args.overwrite,
                logger=logger,
                input_identifiers={"pmid": pmid, "record_id": record_id},
            )

            df.loc[df["record_id"] == record_id, "Include_YN"] = str(parsed.get("Include_YN", "")).strip()
            df.loc[df["record_id"] == record_id, "Reason_Exclude"] = str(parsed.get("Reason_Exclude", "")).strip()
            df.loc[df["record_id"] == record_id, "IndicationBucketHint"] = str(parsed.get("IndicationBucketHint", "")).strip()
            df.loc[df["record_id"] == record_id, "EndpointsTagged"] = ";".join(parsed.get("EndpointsTagged", []) or [])
            df.loc[df["record_id"] == record_id, "TierSuggestedFromAbstract"] = str(parsed.get("TierSuggestedFromAbstract", "")).strip()

            df.loc[df["record_id"] == record_id, "InterventionAliveHint"] = coerce_bool_hint(parsed.get("InterventionAliveHint"))
            df.loc[df["record_id"] == record_id, "RandomizedHint"] = coerce_bool_hint(parsed.get("RandomizedHint"))
            df.loc[df["record_id"] == record_id, "PlaceboHint"] = coerce_bool_hint(parsed.get("PlaceboHint"))
            df.loc[df["record_id"] == record_id, "DoubleBlindHint"] = coerce_bool_hint(parsed.get("DoubleBlindHint"))

            trial_ids = parsed.get("TrialRegistryIDs", []) or []
            df.loc[df["record_id"] == record_id, "TrialRegistryIDs"] = ",".join([str(x).strip() for x in trial_ids if str(x).strip()])
            needs_registry = True if not any(re.match(r"^NCT\\d{8}$", str(x).strip()) for x in trial_ids) else False
            df.loc[df["record_id"] == record_id, "NeedsRegistryCheck"] = needs_registry

            processed += 1
        except Exception as e:
            failures += 1
            ensure_dir(artifacts_dir)
            write_json(artifacts_dir / "error.json", {"error": str(e)}, overwrite=True)
            logger.error("Screening failed for %s: %s", record_id, e)

    if not args.dry_run:
        out_parquet = Path("data/outputs/screening_table.parquet")
        out_csv = Path("data/outputs/screening_table.csv")
        ensure_dir(out_parquet.parent)
        df.to_parquet(out_parquet, index=False)
        df.to_csv(out_csv, index=False)

        if args.table != out_parquet and args.table != out_csv:
            ensure_dir(args.table.parent)
            if args.table.suffix.lower() == ".parquet":
                df.to_parquet(args.table, index=False)
            elif args.table.suffix.lower() == ".csv":
                df.to_csv(args.table, index=False)

        manifest_path = Path("data/intermediate/llm/screening/run_manifest.json")
        manifest = make_run_manifest("screen_abstracts_llm", vars(args), root=root)
        manifest["counts"] = {"processed": processed, "failures": failures}
        write_json(manifest_path, manifest, overwrite=True)


if __name__ == "__main__":
    main()

