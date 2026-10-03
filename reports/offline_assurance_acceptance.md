# Offline assurance acceptance report

**Later fallback update:** Factory artwork was rejected by the user and disabled by default. The figures below describe the earlier bundled-artwork snapshots. See [app_fallback_transition.md](app_fallback_transition.md) for the current app-managed exports and strict pack-media metrics.

Actual snapshot results, 3 October 2026. The implementation is tested; the full dataset acceptance target is not achieved. All four exports remain draft packs. Original v3 sources and downstream City Lab curation were preserved.

## 1. Architecture Audit

The existing factory supplied city resolution, open-data extraction, taxonomy, canonical graphs, enrichment, WebP processing, human curation, quarantine and v3 exporters. Added free-only AI routing, strict decision schemas, media/legal assurance, scoped source evidence, geographic/coordinate checks, grounded metadata recovery, fallback pools, repair orchestration and explicit usability. See docs/architecture-audit.md.

## 2. Files Changed

Important modules: datafactory/ai/{config,providers,router,decisions}.py; models/media_candidate.py; sources/openverse.py; pipeline/{repair,media_assurance,media_policy,identity_assurance,identity_review,geographic_assurance,source_evidence,metadata_assurance,fallbacks,usability,offline_export}.py; canonical graph/city/cache/source adapters; CLI; config/{ai,assurance}.yaml; assets/fallbacks; README; offline tests. Existing user edits and v3 packs were not reverted.

## 3. AI Configuration

Models actually invoked: Groq `qwen/qwen3.8-27b`; Gemini `gemini-3.8-flash`. Both appeared in account model lists and returned successful inference results. The approved alternate `gemini-3.5-flash-lite` was not invoked. Local .env loading keeps keys private and gives process environment precedence. Billing was explicitly confirmed disabled for both keys by the user.

Model/free-tier references: [Groq vision](https://console.groq.com/docs/vision), [Groq limits](https://console.groq.com/docs/rate-limits), [Gemini models](https://ai.google.dev/gemini-api/docs/models), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing). Availability and limits can change.

## 4. Free-Only Verification

AI_MODE: FREE_ONLY. Paid providers invoked: **0**. Paid features invoked: **0**. Only approved Groq/Gemini endpoints/models are permitted; no search/grounding/generation tools. Free account confirmation is a configuration gate, not a vendor billing audit. Quota/service failures are retained as unresolved jobs. Keys never enter report or decision payloads.

## 5. AI Usage

Totals combine the archived initial live pass and the latest repair pass retained in each final export. Jaipur's latest repair pass included 10 further live calls; other latest passes reused cached decisions. One additional Jaipur Groq smoke call and one separate Gemini diagnostic call are excluded from this table and recorded in the linked diagnostic artifacts. Identity review usage appears separately below if authorized.

| City | Groq calls | Gemini calls | Escalations | Cache hits | 429 events |
|---|---|---|---|---|---|
| Manali | 7 | 2 | 2 | 16 | 1 |
| Jaipur | 19 | 11 | 0 | 57 | 12 |
| Udaipur | 13 | 7 | 1 | 36 | 9 |
| Varanasi | 11 | 9 | 0 | 40 | 5 |

## 6. Core Media

Final exported decisions; rejection counts include existing and discovered candidates. No fallback satisfies REAL_REQUIRED.

| City | REAL_REQUIRED | Already valid | Recovered | Rejected | Unresolved |
|---|---|---|---|---|---|
| Manali | 13 | 0 | 0 | 0 | 13 |
| Jaipur | 52 | 0 | 2 | 18 | 50 |
| Udaipur | 55 | 1 | 0 | 16 | 54 |
| Varanasi | 117 | 0 | 5 | 41 | 112 |

## 7. Jaipur 18 Media Cases

All 18 supplied IDs are reported. Three are absent in both current DataFactory JSON and City Lab SQLite. Three published entries have a lower media policy; their contextual artwork does not resolve the downstream real-photo request. No historical ID was silently mapped to a similarly named venue. Full source URLs, creator/license/dimensions, finalist decisions and reasons where available are in reports/jaipur_18_media_cases.json.

| Supplied ID | Current policy | Candidates | Result |
|---|---|---|---|
| yc_in_rj_jaipur_ajmeri_gate | REAL_REQUIRED | 0 | UNRESOLVED_REQUIRED_PHOTO |
| yc_in_rj_jaipur_alice_garg_seashell_museum | REAL_REQUIRED | 0 | UNRESOLVED_REQUIRED_PHOTO |
| yc_in_rj_jaipur_amer_palace | absent | 0 | ID_ABSENT_REVIEW |
| yc_in_rj_jaipur_chulgiri_digamber_jain_temple | REAL_REQUIRED | 0 | UNRESOLVED_REQUIRED_PHOTO |
| yc_in_rj_jaipur_diwan_i_khas | absent | 0 | ID_ABSENT_REVIEW |
| yc_in_rj_jaipur_elejungle_jaipur_elephant_ride | REAL_REQUIRED | 0 | UNRESOLVED_REQUIRED_PHOTO |
| yc_in_rj_jaipur_ganesh_pol | REAL_REQUIRED | 3 | UNRESOLVED_REQUIRED_PHOTO |
| yc_in_rj_jaipur_handicraft_haveli | absent | 0 | ID_ABSENT_REVIEW |
| yc_in_rj_jaipur_iswari_minar_swarga_sali_isarlat | REAL_REQUIRED | 0 | UNRESOLVED_REQUIRED_PHOTO |
| yc_in_rj_jaipur_jaipur_palace | REAL_PREFERRED | 0 | DOWNSTREAM_POLICY_MISMATCH_REVIEW |
| yc_in_rj_jaipur_jhalanaamagarh_leopard_conservation_reserve | REAL_REQUIRED | 0 | UNRESOLVED_REQUIRED_PHOTO |
| yc_in_rj_jaipur_lakkar_haveli | FALLBACK_ALLOWED | 0 | DOWNSTREAM_POLICY_MISMATCH_REVIEW |
| yc_in_rj_jaipur_lohaghar_fort | FALLBACK_ALLOWED | 0 | DOWNSTREAM_POLICY_MISMATCH_REVIEW |
| yc_in_rj_jaipur_nahargarh_wildlife_sanctuary | REAL_REQUIRED | 0 | UNRESOLVED_REQUIRED_PHOTO |
| yc_in_rj_jaipur_nakati_mata_temple | REAL_REQUIRED | 0 | UNRESOLVED_REQUIRED_PHOTO |
| yc_in_rj_jaipur_sawai_mansingh_townhall | REAL_REQUIRED | 0 | UNRESOLVED_REQUIRED_PHOTO |
| yc_in_rj_jaipur_suraj_pol_gate | REAL_REQUIRED | 3 | UNRESOLVED_REQUIRED_PHOTO |
| yc_in_rj_jaipur_vidyadhar_garden | REAL_REQUIRED | 3 | UNRESOLVED_REQUIRED_PHOTO |

## 8. Identity Resolution

Located City Lab candidate manifests read-only. These collisions originate in upstream name-based canonical IDs. New builds disambiguate colliding IDs from sorted source IDs, coordinates and category. The report proposes IDs only: no historical migration, merge or downstream edit was applied. AI opinions never waive missing factual corroboration.

| City | Groups found | Members | Auto-resolved | Review/unresolved | Classification |
|---|---|---|---|---|---|
| Jaipur | 13 | 29 | 0 | 13 | {'UPSTREAM_CANONICAL_ID_BUG': 13} |
| Udaipur | 3 | 6 | 0 | 3 | {'UPSTREAM_CANONICAL_ID_BUG': 3} |
| Varanasi | 3 | 7 | 0 | 3 | {'UPSTREAM_CANONICAL_ID_BUG': 3} |

City Lab external AI opinions require explicit transfer authorization after automatic approval review rejected the initial request. Local identity audits completed successfully; each report records actual AI usage and zero downstream files modified.

## 9. Coordinates

The Jaipur geographic benchmark retains original/source points, bbox, regional associations and distances in reports/jaipur_geographic_benchmark.json. Nakati Mata Temple is 18.393 km from the center, outside the municipal bbox, with only one independent coordinate source. Outcome: review regional association; do not move its coordinates or assert a wrong city. Two Jaipur published records also have suspicious coordinate comparisons. Automatic repairs require two independent sources agreeing and a supported destination-region outcome.

| City | Coordinate reviews | Automatic repairs |
|---|---|---|
| Manali | 1 | 0 |
| Jaipur | 2 | 0 |
| Udaipur | 1 | 0 |
| Varanasi | 0 | 0 |

## 10. Metadata Recovery

Source text remains factual provenance; Groq/Gemini only assist bounded extraction. Stale, ambiguous or conflicting hours remain unknown/unverified. Entity tags require the entity's own name and coordinates to corroborate the place; an OSM QID alone is insufficient.

| City | Hours | Descriptions | Entity links | Addresses |
|---|---|---|---|---|
| Manali | 0 | 8 | 0 | 0 |
| Jaipur | 0 | 36 | 1 | 0 |
| Udaipur | 0 | 0 | 0 | 0 |
| Varanasi | 0 | 3 | 0 | 0 |

## 11. Fallback Diversity

216 self-authored CC0 procedural illustrations: eight variants in each of 27 contextual categories. Stable SHA-256 assignment uses the full canonical ID. Real media and contextual art are labelled separately. Smaller categories naturally use fewer variants; asset sharing counts remain visible.

| City | Before fallback POIs | After fallback POIs | Distinct assets used | Largest sharing |
|---|---|---|---|---|
| Manali | 0 | 1688 | 51 | 173 |
| Jaipur | 0 | 626 | 88 | 34 |
| Udaipur | 0 | 267 | 69 | 21 |
| Varanasi | 0 | 226 | 59 | 21 |

## 12. Usability

A POI must have source-backed identity, valid category/coordinates/region, renderable local primary/thumbnail media where required, complete media provenance, and no critical anomaly. REAL_REQUIRED additionally needs visually verified authentic media. Hours, description and address coverage are separate; no mandatory factual fill is fabricated. Source readiness requires ≥95% usability and zero critical blockers.

| City | Published | Usable | Usable % | Critical POIs |
|---|---|---|---|---|
| Manali | 1702 | 1682 | 98.82 | 20 |
| Jaipur | 684 | 633 | 92.54 | 51 |
| Udaipur | 324 | 269 | 83.02 | 55 |
| Varanasi | 348 | 236 | 67.82 | 112 |

## 13. Offline Readiness

Draft readiness represents structural bundle validity and reviewability. It does not certify unresolved facts or media. Checksum, schema, JSONL/Parquet/SQLite projections, SQLite integrity and local image decode checks passed for all listed exports. Broken or duplicate optional gallery entries were pruned from these new exports, with each removal recorded; the original source packs were preserved. No referenced primary, thumbnail or gallery asset is missing in the final bundles.

| City | DRAFT_OFFLINE_READY | SOURCE_DATA_READY | Actual output |
|---|---|---|---|
| Manali | True | False | C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\himachal_pradesh\manali\v3-offline-validated |
| Jaipur | True | False | C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\rajasthan\jaipur\v3-offline-validated |
| Udaipur | True | False | C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\rajasthan\udaipur\v3-offline-validated |
| Varanasi | True | False | C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\uttar_pradesh\varanasi\v3-offline-validated |

| City | Optional gallery entries pruned | Pipeline health | Legacy semantic quality | Legacy source coverage |
|---|---|---|---|---|
| Manali | 10 | PASS | PASS | PASS |
| Jaipur | 30 | PASS | PASS | WARN |
| Udaipur | 38 | PASS | PASS | PASS |
| Varanasi | 64 | PASS | PASS | WARN |

## 14. Generalization Test

Manali uses the same repair code against its existing 1,702-place snapshot, with no city-specific branches. Sparse authoritative/media coverage leaves 13 required photos unresolved despite 98.82% published usability. This is a cached-source repair/generalization test, not a fresh all-source extraction or manual destination certification. Core production source/pipeline/AI behavior contains no Jaipur attraction-name branches; legacy audit dashboards retain their fixed benchmark corpus.

## 15. Tests

Command: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=scratch/test-assurance-final-8 --tb=short`: **149 passed in 23.84 seconds**. Default tests disable live HTTP and use fixtures/MockTransport. Coverage includes strict output, free account/endpoint gating, quota cooldown/fallback/cache, city isolation, image legality/quality/identity, coordinates, grounded hours/text, fallback invariants, human locks, collision IDs, read-only identity auditing and transactional export consistency. Actual live CLI: ai-status; one-image ai-smoke; repair --apply --network for Jaipur/Udaipur/Varanasi; cached repair for Manali; final re-exports with zero inference budget. All final bundles passed validate_release_package. Repository-wide git diff --check also reports pre-existing generated HTML whitespace; source packs were left unchanged.

Production-name scan: `rg -n 'Jaipur|Udaipur|Varanasi|Amber Fort|Hawa Mahal' datafactory`. CLI has three Jaipur help examples. classify.py has two illustrative hotel/shop comments. audit/generalization_evaluator.py has a benchmark description, three fixed dataset descriptors and one report caption; audit/dashboard.py has four report captions/example descriptions; audit/search_engine.py and audit/independent_verifier.py each have one explanatory docstring. These are examples, benchmark definitions and report text. Amber Fort and Hawa Mahal have no occurrences. There are no matching city-specific extraction, repair or AI decision branches.

## 16. Remaining Limitations

Full dataset acceptance is **not achieved**. Jaipur/Udaipur/Varanasi remain below 95%; all cities have required real-media blockers. Source discovery/research and AI budgets deliberately bound each pass. Groq free quota and Gemini temporary high-demand errors deferred work. Openverse results require original-source license verification; the implemented automatic verification adapter currently supports Commons originals, while other original hosts stay in review. Descriptions are conservative source excerpts; no schedule was recovered in these snapshots. The 18-case mismatch and 19 historical identity groups require source research/review and any eventual published-ID migration requires approval. Missing facts and photos remain explicit. City Lab's broken human media overrides and manual certification state were not changed. Temporary failed exports/older snapshots are preserved for recovery and ignored by Git. Reports expose no API keys.
