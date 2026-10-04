# Jaipur round-two research import

Input: `C:\Users\girir\Documents\YatraCanvas-DataFactory\data\research\import_inputs\jaipur_round2_research_results.json`
Input SHA-256: `bce49b0c66238c0d39a423638480db57a25c3e937fbb4127b01156db113e6abe`
Schema: `1.0`. Registered handoff: `handoff_52e106bcb2e1e8881d37ee23`.
Source: `C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\rajasthan\jaipur\v3-research-jaipur-images-02-derivative-01`

## Dry Run

All 16 REAL_PRIMARY_IMAGE tasks matched; no structural failures. No source/task/place/pack changes or network/AI calls occurred during dry run.

| Metric | Count |
|---|---:|
| tasks_supplied | 16 |
| matched | 16 |
| valid | 16 |
| auto_applicable | 0 |
| review | 7 |
| rejected | 0 |
| missing_pois | 0 |
| invalid_sources | 5 |
| invalid_schedules | 0 |
| media_requiring_verification | 7 |
| unresolved | 9 |

Reason codes: ORIGINAL_SOURCE_LICENSE_UNVERIFIED (5), MEDIA_DOWNLOAD_OR_VERIFICATION_REQUIRED (1), RESEARCH_UNRESOLVED (9), RESEARCH_CONFLICT (1). The 5 dry-run invalid_sources counts represent unverified original-source licenses; network apply verified them all. No IMAGE_SOURCE_INVALID, IMAGE_LICENSE_INVALID, INVALID_RESULT_SCHEMA, UNKNOWN_PLACE_ID, or TASK_ID_OR_PLACE_ID_MISMATCH_OR_DUPLICATE occurred.

## Apply

Command: `.\.venv\Scripts\python.exe -m datafactory.cli research-import --file data\research\import_inputs\jaipur_round2_research_results.json --apply --network --output-version v3-research-jaipur-images-03`

Accepted/applied: **1**; review: **6**; rejected: **0**; unresolved: **9**.
All 16 tasks matched and remained schema-valid. Apply invalid sources/schedules/missing POIs: 0.

## Images Accepted

Anokhi Museum of Hand Printing: exact verified Wikidata P18 evidence plus independently verified Commons creator/license and existing-asset reuse. Existing image bytes retained; provenance and assurance upgraded in the new pack only.

## Images Still Blocked

Downloaded successfully: 6. Deterministic rejects: 0. License holds: 0. Duplicate holds: 0. SigLIP ranked 5; its scores did not override assurance. One confirmed MPO image was normalized through the existing primary-frame pathway.

- Jantar Mantar and Jawahar Circle: MEDIA_ASSURANCE_THRESHOLD_NOT_MET, with unmet mobile_card_suitability.
- Jhalana–Amagarh reserve, Man Gate, and Sawai Mansingh Townhall: AI_UNAVAILABLE / IDENTITY_EVIDENCE_INSUFFICIENT; Groq HTTP 429 (HTTP_RATE_LIMIT) and Gemini HTTP 503 (HTTP_SERVER_ERROR) prevented completed cloud verification. Local SigLIP remained ambiguous.
- India Gate: RESEARCH_CONFLICT; supplied identity conflict retained for review.
- Nine results were supplied UNRESOLVED and remain unresolved.

## Jaipur Before vs After

| Metric | Before | After |
|---|---:|---:|
| Verified REAL_REQUIRED images | 16 | 17 |
| REAL_REQUIRED coverage (%) | 30.77 | 32.69 |
| General usability (%) | 3.22 | 3.36 |
| Critical blocker POIs | 662 | 661 |
| Source data ready | False | False |
| Remaining REAL_REQUIRED blockers | 36 | 35 |

## Output Pack

`C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\rajasthan\jaipur\v3-research-jaipur-images-03`

validate_release_package passed: JSON/JSONL/Parquet/SQLite, media, and checksums. Pipeline health PASS; data quality PASS; zero semantic errors. Source coverage WARN and source readiness false remain visible.

## Safety

All **24,112 protected file hashes matched**. Original v3, all existing releases/source packs, registered handoffs, human curation, application code, and FREE_ONLY configuration unchanged. The previous 16 verified images and their 32 primary/thumbnail files are identical in the new pack. City Lab was untouched. Published place/task IDs were preserved. The normal research importer alone wrote its new audit and advanced the Jaipur head to the validated new pack.

Reported assurance calls: 4 (Groq 3, Gemini 1). Paid providers invoked: 0; paid AI calls: 0. Assurance policy and thresholds were not modified.

## Remaining Work

35 REAL_REQUIRED images remain unverified across Jaipur. The 3 provider-held candidates retain verified source/media evidence; the 2 suitability failures need suitable alternatives; the conflict and unresolved tasks need further identity/evidence research. Generate a fresh registered handoff from the new head before another import; previous handoffs retain their original snapshots.

Detailed files: dry-run.json, apply.json, before.json, verification.json, plus stderr logs in this report directory.
