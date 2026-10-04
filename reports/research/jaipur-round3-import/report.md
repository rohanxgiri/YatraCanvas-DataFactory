# Jaipur Round 3 import

Registered handoff: `handoff_7b483895bbeed22d7bd2e61f`.
Input: `C:\Users\girir\Documents\YatraCanvas-DataFactory\data\research\import_inputs\jaipur_round3_research_results.json`
Input SHA-256: `a006ed58d6ead0e1203d8758fa698dfd68134c4c0e3159452d5be41fa78e3eea`.

## Dry Run

10 supplied, 10 matched, 10 valid; 0 structural failures. Review 1, rejected 0, unresolved 9. Missing POIs 0, invalid schedules 0, auto-applicable 0. The single invalid_sources count was ORIGINAL_SOURCE_LICENSE_UNVERIFIED awaiting fresh Commons metadata. Dry-run AI calls: 0.

## Network Apply

Accepted/applied **0**; review **1**; rejected **0**; unresolved **9**. Apply invalid sources: 0. The registered import audit was saved.

```powershell
.\.venv\Scripts\python.exe -m datafactory.cli research-import --file data\research\import_inputs\jaipur_round3_research_results.json --apply --network --output-version v3-research-jaipur-images-04
```

## Jantar Mantar decision

**REVIEW — MEDIA_ASSURANCE_THRESHOLD_NOT_MET**.

Candidate: [Samrat yantra at jantar mantar ,Jaipur.jpg](https://commons.wikimedia.org/wiki/File:Samrat_yantra_at_jantar_mantar_,Jaipur.jpg)

Commons creator and CC BY-SA 4.0 license verified. The 4608 × 2592 JPEG downloaded successfully and passed deterministic file/media checks. SigLIP remained AMBIGUOUS.

| Assurance field | Result | Required |
|---|---:|---:|
| Overall confidence | 0.85 | ≥0.90 |
| Identity confidence | 0.95 | ≥0.90 |
| Landmark prominence | 0.85 | ≥0.65 |
| Mobile-card suitability | 0.90 | ≥0.70 |
| Watermark or obstruction flagged by Groq | true | false |

Groq returned a raw ACCEPT recommendation, but the existing independent assurance gates correctly held it because overall confidence was 0.85 and watermark_or_obstruction was true. This is an automated flag, not a manually confirmed watermark finding. The exact unmet fields are confidence and identity_or_photo_safety.

Gemini second-opinion verification failed with HTTP 503, AI_UNAVAILABLE / HTTP_SERVER_ERROR. The stronger card composition did not override the remaining confidence and photo-safety requirements.

## Coverage Before vs After

| Metric | Before | After |
|---|---:|---:|
| Verified REAL_REQUIRED | 17/52 | 17/52 |
| REAL_REQUIRED coverage | 32.69% | 32.69% |
| Remaining required media | 35 | 35 |
| General usability | 3.36% | 3.36% |
| Critical blocker POIs | 661 | 661 |
| Source data ready | false | false |

## Output and Validation

No new pack was published: the existing importer publishes a new immutable release only when at least one result passes assurance. `v3-research-jaipur-images-04` was not created. The latest head remains:
`C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\rajasthan\jaipur\v3-research-jaipur-images-03`

The retained pack passed validate_release_package: pipeline health PASS, data quality PASS, zero semantic errors; source coverage WARN remains visible.

## Safety

All **24,236 protected file hashes matched**. Original v3, previous releases/source packs, all 17 accepted images, human curation, configuration, importer and assurance code unchanged. Head unchanged. City Lab untouched. Original input bytes preserved. No thresholds, IDs or production data were edited manually.

FREE_ONLY assurance calls: **2** (Groq 1, Gemini 1). Paid providers invoked: **0**; paid AI calls: **0**.

No application code changed; verification used the existing import dry run, network apply, release validator and preservation audit.

## Files

- Apply decisions: `C:\Users\girir\Documents\YatraCanvas-DataFactory\reports\research\jaipur-round3-import\apply.json`
- Verification: `C:\Users\girir\Documents\YatraCanvas-DataFactory\reports\research\jaipur-round3-import\verification.json`
- Registered audit: `C:\Users\girir\Documents\YatraCanvas-DataFactory\data\research\imports\424490dd0bb74df403c5fa9d0753e1e6c6f59f3eaac0c2cbad53c525bc0948b4.json`

Jantar Mantar needs review of the flagged watermark/obstruction and confidence hold before acceptance; the nine unresolved tasks still need reusable exact-POI evidence.
