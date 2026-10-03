# Review — Offline source assurance

Reviewed against the user request and `docs/architecture-audit.md`, 3 October 2026.

## Layer 1 — Plan alignment

ISSUES FOUND.

The generic implementation covers free-only routing, city-scoped caches, source
evidence, media policies and visual inspection, identity/geographic checks, grounded
metadata, contextual fallback pools, immutable v3 exports and explainable usability.
The same repair pipeline was exercised with Jaipur, Udaipur, Varanasi and Manali.
The report includes all 18 supplied Jaipur IDs and the downstream identity manifests.

- **Important:** Dataset acceptance remains unmet. Jaipur, Udaipur and Varanasi are
  below 95% usable. Manali exceeds that percentage but retains critical blockers.
- **Important:** Required photos remain unresolved: Jaipur 50, Udaipur 54,
  Varanasi 112, Manali 13. The supplied 18-case benchmark has no verified resolution;
  three IDs are absent and three have a downstream policy mismatch.
- **Important:** All 19 historical canonical-ID conflict groups remain in review.
  Future candidate-ID disambiguation is implemented; published-ID migration and
  downstream merges were not applied.

## Layer 2 — System integrity

PASS for reviewed implementation paths and verification evidence.

AI decisions stay separate from factual provenance. Exact license checks, source
corroboration and local asset validation precede acceptance. Required photos cannot
be replaced by artwork. Existing human locks and published IDs are preserved.
No city-name decision branches were found in the extraction/repair/AI paths; the
remaining name matches are help examples, comments and legacy benchmark/report text.
Exports use existing v3 schemas and SQLite projections with additive sidecars.
City Lab manifests were inspected read-only and their SHA-256 values checked.

## Layer 3 — Production readiness

ISSUES FOUND for dataset certification; structural export verification passed.

- **Important:** Free quota and temporary provider unavailability deferred inference.
  Explicit budgets, cooldowns, cached decisions and unresolved jobs retain those
  failures without fabricating replacements.
- **Important:** Automatic original-source license verification supports Commons
  originals. Other Openverse original hosts require review.
- **Important:** Cross-city proof used existing snapshots. It does not certify fresh
  extraction coverage or each destination's factual completeness.

149 offline tests passed in 23.84 seconds with live HTTP disabled by default.
All four final bundles passed checksum, schema, JSONL/Parquet/SQLite consistency,
SQLite integrity and referenced-image decode checks. Optional gallery removals are
recorded. No keys were intentionally included in logs, reports or fixtures; the
final artifact scan is recorded separately in `reports/offline_final_verification.json`.

## Summary

Six remaining issues across plan alignment and dataset production readiness.
Implementation validation passed; all four packs remain drafts. See the full
16-section report in `reports/offline_assurance_acceptance.md` for actual counts,
provider usage, output paths and evidence.

Automatic approval review rejected external transfer of the City Lab candidate
payload. Local audits completed. Sending reduced public identity fields to Groq or
Gemini remains pending explicit user authorization; no rejected transfer was sent.
