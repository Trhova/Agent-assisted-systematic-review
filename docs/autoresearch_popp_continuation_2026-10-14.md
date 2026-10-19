# Popp acquisition continuation —14October2026,04:13UTC

This cycle closes a demonstrated source integration gap while preserving the original failed Popp run. `scripts/import_source_pdf.py` provides a reusable route for originals already lawfully retrieved outside the automatic downloader. It requires an HTTP200 receipt with the exact PDF SHA256, public HTTPS provenance, a real PDF signature and DOI/title identity on the first page. It reparses with the existing page-aware PDF parser rather than trusting supplied extracted text. Original PDF/receipt are retained and nonempty destinations cannot be overwritten. An actual import of PMID32445400 succeeded; its DOI is verified on page1.

`ASR_ACQUISITION_CACHE_ONLY=1` lets PublicFetcher replay validated successful caches without retrying expired failures or new URLs. `ASR_WEB_DISCOVERY=0` disables additional model-assisted source discovery for this bounded continuation. Bibliographic database search and authenticated model decisions remain live. The mode is recorded in run status; this is developer-assisted cached-source development, not fresh autonomous source discovery. The old generic continuous-only limitation sentence is corrected in the new code only.

Validation:200 tests passed, selected fatal/import lint passed. New tests cover successful source import and preserved raw artifacts, destination overwrite refusal, mismatched checksum, failed HTTP status, credential-bearing URL, wrong article identity, HTML masquerading as PDF, and cache-only refusal to perform network requests while validated successes still replay. Actual original-PDF import complements these unit checks.

Lopes adjudication used the original30July2020 ReBEC registration plus the original primary paper. Mortality is specified but no scheduled21–28-day mortality horizon is established. Ten-day treatment is not follow-up; observed individual hospital stays do not resolve missing common outcome timing. No scientific eligibility, denominator, estimator, tolerance or completion gate changed. Evidence and reasons are in `benchmarks/findings/popp2021_lopes_followup_adjudication_v1.json`; raw registry web capture is preserved separately from the direct HTTP403. The remaining letters were checked through a publisher PDF route and a French HAL repository query. Audit showed the publisher URL had already been attempted in v1, so that403 is not new access evidence and must not be repeated. The initial HAL query returned an API error, not a valid negative search; a corrected query receipt is retained separately. The corrected HAL query found the matching record, but its metadata declares openAccess_bool=false with no file URL. A genuinely new NCBI BioC route for PMID32337546 returned no article result. No new original emerged. Receipts and error distinctions are in `benchmarks/findings/popp2021_remaining_source_routes_v2.json`. Repeating old failures is disabled in the numerical continuation.

The isolated run is `data/benchmarks/popp2021_v2/popp2021_hospital_mortality_development_v1/d2cc93475219`. `preregistration_final.json` supersedes a preserved unlaunched draft after adding cache-only safeguards. Final source manifest is `benchmarks/sources/popp2021_continuation_manifest_v2_final.json`. Code49a974e7781395e97d3aea388efca21d6e95c5b32c056f355c604977516ac2c3; original protocol d2cc93475219520b598aac86f7dca809b98468d32ba2518ec2db5215e2b35d95. Reference numerical targets remain evaluator-only. Original source caches, not previous model decisions or extracted rows, were copied. Suite PID11241 launched with explicit gpt-6-astra/codex, worker medium; nested effort backend-default/unpinned, two bounded rounds.

```bash
ASR_ACQUISITION_CACHE_ONLY=1 ASR_WEB_DISCOVERY=0 .venv/bin/python -m scripts.benchmark_suite --suite benchmarks/suite_popp2021_v2.yaml --workdir data/benchmarks/popp2021_v2 --backend codex --model gpt-6-astra --max-rounds 2
```

This identifies the actual submission; check the live checkpoint before any continuation and never duplicate an active runner. Execution completed and PID11241 exited.132 records screened,9 full-text attempts,2 independent effects, **3 unresolved (down from4)**. The imported letter was excluded as non-trial by the fresh model. Both mortality event counts and denominators are unchanged:1/55 versus4/50;1173/5610 versus1190/5730. **RR1.004034533[0.934579543,1.078651198]**, I²45.264%, still matches the published two-contributor outcome. **Overall reproduction remains false** because the two inaccessible letters and Lopes follow-up remain unresolved. No gate changed.

Artifact audit valid with zero issues; two source-checked RoB drafts, zero unverified. These are automated drafts, not expert validation.200 tests pass;12 configured protocol/reference pairs verify. The original18 audited artifacts remain unchanged. Actual suite report and review export are under the run directory; machine-readable cycle summary is `benchmarks/findings/popp2021_continuation_v2.json`. No numerical/model runner remains active.

Next work should address outcome-availability reporting generically, separating missing report access, eligible trial with unidentified target timing, and accepted data with source-reported follow-up limitations. Keep the existing completion gate until any change has explicit methodological justification and a separately frozen policy. Further Popp reruns require genuinely new original-source evidence; unchanged retries are not useful. A later evaluation can use the binary capability with an independently qualified review, but this checkpoint does not establish several-review or held-out validation.


Reusable import command (choose an empty destination; existing sources are never replaced):

```bash
.venv/bin/python -m scripts.import_source_pdf --pdf data/benchmarks/popp2021_followup_sources_v1/PMC7283693.pdf --receipt data/benchmarks/popp2021_followup_sources_v1/receipt.json --record data/benchmarks/popp2021_followup_sources_v2/32445400_record.json --destination data/benchmarks/manual_import_example/32445400
```

The actual continuation used this same importer function before freezing its final manifest. All18 original v1 audit-tracked artifacts still match their recorded hashes after the isolated continuation.

Actual model requests: 15 review and 4 RoB, explicit gpt-6-astra.
