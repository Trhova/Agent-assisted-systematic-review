from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.utils import (
    add_common_args,
    call_llm_json,
    ensure_dir,
    load_table,
    make_run_manifest,
    parse_only_list,
    setup_logging,
    stable_screening_columns,
    write_json,
)


def _load_fulltext_text(record_id: str) -> str:
    path = Path("data/intermediate/fulltext_text") / f"{record_id}.json"
    if not path.exists():
        return ""
    obj = json.loads(path.read_text(encoding="utf-8"))
    pages = obj.get("pages") or []
    chunks = []
    for p in pages:
        t = (p.get("text") or "").strip()
        if t:
            chunks.append(t)
        if sum(len(c) for c in chunks) > 60_000:
            break
    return "\n\n".join(chunks).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM full-text extraction with structured outputs.")
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

    included = df[df["Include_YN"].astype(str).str.upper().str.strip() == "Y"].copy()
    if only:
        included = included[included["record_id"].astype(str).isin(only)]
    if args.limit and args.limit > 0:
        included = included.head(args.limit)

    schema_path = Path("protocol/schemas/extraction.schema.json")
    prompt_path = Path("protocol/prompts/extract_fulltext.md")
    base_dir = Path("data/intermediate/llm/extraction")
    ensure_dir(base_dir)

    processed = 0
    failures = 0
    for _, row in included.iterrows():
        record_id = str(row["record_id"])
        pmid = str(row["PMID"])
        artifacts_dir = base_dir / record_id

        if args.dry_run:
            logger.info("Dry run: would extract %s (%s)", record_id, pmid)
            continue

        fulltext = _load_fulltext_text(record_id)
        if not fulltext:
            ensure_dir(artifacts_dir)
            write_json(artifacts_dir / "error.json", {"error": "missing_fulltext_text"}, overwrite=True)
            failures += 1
            continue

        try:
            input_text = f"PMID: {pmid}\nTitle: {row.get('Title','')}\n\nFULLTEXT_EXTRACT:\n{fulltext}"
            pdf_path = Path("data/raw/pdfs") / f"{record_id}__{pmid}.pdf"
            fulltext_json_path = Path("data/intermediate/fulltext_text") / f"{record_id}.json"
            parsed = call_llm_json(
                step="extraction",
                record_id=record_id,
                input_text=input_text,
                prompt_path=prompt_path,
                schema_path=schema_path,
                artifacts_dir=artifacts_dir,
                overwrite=args.overwrite,
                logger=logger,
                input_identifiers={
                    "pmid": pmid,
                    "record_id": record_id,
                    "pdf_path": str(pdf_path),
                    "fulltext_json_path": str(fulltext_json_path),
                },
            )

            for field in [
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
            ]:
                df.loc[df["record_id"] == record_id, field] = str(parsed.get(field, "")).strip()

            processed += 1
        except Exception as e:
            ensure_dir(artifacts_dir)
            write_json(artifacts_dir / "error.json", {"error": str(e)}, overwrite=True)
            failures += 1
            logger.error("Extraction failed for %s: %s", record_id, e)

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

        manifest_path = Path("data/intermediate/llm/extraction/run_manifest.json")
        manifest = make_run_manifest("extract_fulltext_llm", vars(args), root=root)
        manifest["counts"] = {"processed": processed, "failures": failures}
        write_json(manifest_path, manifest, overwrite=True)


if __name__ == "__main__":
    main()
