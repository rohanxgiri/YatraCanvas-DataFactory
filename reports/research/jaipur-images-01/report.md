# Jaipur image research import

Schema: `1.0`; registered handoff: `handoff_fc76540c1776ad82dd87071b`; 50 `REAL_PRIMARY_IMAGE` results.

### Dry Run

Original bundle located in Downloads; preserved byte for byte in `C:\Users\girir\Documents\YatraCanvas-DataFactory\data\research\import_inputs\jaipur_image_research_results.json`.
Safe input-only corrections: 34 Creative Commons URL trailing slash corrections and 1 Unicode-equivalent creator spelling; all IDs and factual claims preserved. Original Downloads file and repository copy unchanged. No IDs, license claims, attribution, source evidence or status were altered.

| Counter | Original dry run | Corrected dry run | Network apply |
|---|---:|---:|---:|
| `tasks_supplied` | 50 | 50 | 50 |
| `matched` | 50 | 50 | 50 |
| `valid` | 50 | 50 | 46 |
| `auto_applicable` | 0 | 0 | 1 |
| `review` | 42 | 42 | 37 |
| `rejected` | 0 | 0 | 4 |
| `missing_pois` | 0 | 0 | 0 |
| `invalid_sources` | 15 | 0 | 0 |
| `invalid_schedules` | 0 | 0 | 0 |
| `media_requiring_verification` | 42 | 42 | 37 |
| `unresolved` | 8 | 8 | 8 |
| `applied` | 0 | 0 | 1 |

Original reasons: 15 `ORIGINAL_SOURCE_LICENSE_UNVERIFIED`, 20 `ORIGINAL_SOURCE_METADATA_CONFLICT`, 1 `RESEARCH_PARTIAL`, 6 `RESEARCH_CONFLICT`, 8 `RESEARCH_UNRESOLVED`. The 15 verification holds counted as invalid_sources are expected dry-run deferrals, not structural failures.
Corrected reasons: 34 `MEDIA_DOWNLOAD_OR_VERIFICATION_REQUIRED`, 1 `ORIGINAL_SOURCE_METADATA_CONFLICT`, 1 `RESEARCH_PARTIAL`, 6 `RESEARCH_CONFLICT`, 8 `RESEARCH_UNRESOLVED`. Both dry runs had no structural failure codes.

Audit: [input_corrections.json](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-images-01/input_corrections.json); [dry_run.json](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-images-01/dry_run.json); [dry_run_corrected.json](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-images-01/dry_run_corrected.json).

### Apply

First apply published nothing because metadata formatting remained mismatched. After the audited corrections and parser repair: **1 applied, 37 review, 4 rejected, 8 unresolved**. Existing network-enabled CLI published `C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\rajasthan\jaipur\v3-research-jaipur-images-01`.

The narrow importer repair uses urlsplit to preserve semicolons in Commons filenames. Exact source, creator, license and license URL checks and all downstream assurance remain intact. Focused regression tests: 43 passed; git diff --check passed.

Final validation: pipeline health PASS; data quality PASS; source coverage WARN. [validate.stdout.txt](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-images-01/validate.stdout.txt).

### Images Accepted

33 downloaded successfully. One accepted and processed into offline primary/thumbnail WebP: **Akshardham Temple**. Creator Pranavdadhich; CC BY-SA 3.0. Published media verification signature and identity binding match the actual output assets. Real SigLIP ran on 13 candidates; existing assurance made final acceptance decisions. Free inference calls: 8 Groq + 3 Gemini; paid calls 0.

### Images Still Blocked

| Category | Count | Exact reason / root cause |
|---|---:|---|
| Duplicate holds | 16 | DUPLICATE_IMAGE against existing POI media |
| Deterministic rejects | 4 | ACTUAL_MIME_UNSUPPORTED: actual Pillow format MPO although Commons declared JPEG |
| License metadata hold | 1 | ORIGINAL_SOURCE_METADATA_CONFLICT: Lake Palace CC0 naming/URL differs; Commons HTTP license URL fails existing HTTPS policy |
| Identity/quality/cloud holds | 12 | Five fail existing assurance thresholds; seven AI_UNAVAILABLE, including Groq quota/cooldown and unavailable Gemini inference |
| Download hold | 1 | MEDIA_DOWNLOAD_OR_VERIFICATION_REQUIRED: Govind Devji file 24,469,664 bytes exceeds 20,000,000-byte limit |
| Partial/conflicting research | 7 | RESEARCH_PARTIAL 1, RESEARCH_CONFLICT 6 |
| Unresolved research | 8 | RESEARCH_UNRESOLVED |

No assurance thresholds, MIME allowlist, byte limits, license requirements, provider settings or validation policies were changed. Gemini read-only model metadata GET succeeded after import; the importer only retains AI_UNAVAILABLE for failed inference, so its precise HTTP status/root cause is unavailable in the saved evidence. Groq recorded two rate-limit responses.

Detailed evidence: [image_audit.json](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-images-01/image_audit.json); [assurance_details.json](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-images-01/assurance_details.json); [blocked_network_diagnostics.json](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-images-01/blocked_network_diagnostics.json).

### Jaipur Before vs After

| Metric | Before | After |
|---|---:|---:|
| GENERAL_USABILITY | 1.17 | 1.32 |
| REAL_REQUIRED_MEDIA_COVERAGE | 3.85 | 5.77 |
| real_required_verified | 2 | 3 |
| critical_blocker_pois | 676 | 675 |
| SOURCE_DATA_READY | False | False |
| MEDIA_NOT_RENDERABLE | 644 | 643 |
| CORE_MEDIA_UNRESOLVED | 50 | 49 |
| COORDINATE_INVALID_OR_CONFLICT | 2 | 2 |
| TRAVEL_REGION_SUSPICIOUS | 2 | 2 |

Published POIs remain 684; required-media total remains 52. Source readiness remains false.

23,626 protected files rehashed: no changed or missing files. Original v3 and every existing release/source pack unchanged; human curation unchanged; registered handoffs unchanged; original research input unchanged; FREE_ONLY configuration unchanged. City Lab unchanged: no files or operations touched it. Paid AI calls = 0. [after.json](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-images-01/after.json).

### Output Pack

C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\rajasthan\jaipur\v3-research-jaipur-images-01

Contains independently validated JSON, JSONL, Parquet, SQLite, processed offline media, licenses, checksums, provenance, import audit, and usability reports.

[summary.json](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-images-01/summary.json) contains the consolidated machine-readable report.

### Remaining Work

Resolve the 49 unapplied results: find distinct standard JPEG/PNG/WebP replacements for duplicate/MPO candidates, verify the held CC0 source metadata, use a permitted smaller Govind image, complete missing/conflicting research, and resolve free-provider availability/quota before retrying assurance. Albert Hall remains held at confidence 0.85 < 0.9; Jhalana/Isarlat wrong-place risk 0.1 > 0.05; Galwar Bagh risk 0.2 > 0.05.

Generate a fresh registered handoff from the new research head before importing further results. Reusing or editing old IDs to bypass the head/snapshot protection is not permitted.
