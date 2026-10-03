# DataFactory optimization and validation

## A. Baseline

Before prioritization, all 1,637 tasks were preserved and audited in `research_baseline.json/md`. The old selector considered every REAL_PREFERRED POI important across unrelated fields and exported P4 by default. Raw missing fields therefore became human work even when not useful for itinerary planning.

| City | Raw unresolved | Optional old P4 | Required-media-policy tasks |
|---|---:|---:|---:|
| Jaipur | 771 | 301 | 158 |
| Udaipur | 264 | 83 | 151 |
| Varanasi | 471 | 174 | 351 |
| Manali | 131 | 51 | 40 |

Baseline types: {'REAL_PRIMARY_IMAGE': 494, 'COORDINATE_RESEARCH': 14, 'OPENING_HOURS': 520, 'DESCRIPTION': 345, 'WEBSITE': 264}.
Baseline tiers: {'core_destination': 700, 'support': 4, 'recommended': 931, 'discovery': 2}.
Baseline categories: {'heritage': 547, 'museum': 44, 'viewpoint': 14, 'park': 523, 'religious': 147, 'hotel': 4, 'arts_culture': 273, 'nature': 46, 'experience': 37, 'food': 1, 'cafe': 1}.

The new deterministic rules classify 261 of these baseline conditions as DO_NOT_RESEARCH, 487 as OPTIONAL_DEFER, and 430 as useful P3 research for later. The complete per-task decisions remain in `research_prioritization.json`. Internal inventories additionally include ordinary gaps that the old selector never generated; their counts are deliberately separate from the fixed baseline.

## B. Real SigLIP

Configured model: `google/siglip-base-patch16-224`; revision `7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed`; actual weights downloaded into `data/cache/models`; real CPU inference PASS. Cache-only offline health also PASS. Duplicate, fuzzy text, geometry and hours checks PASS; optional semantic embeddings remain disabled.

Eight POIs, 24 actual cached photographs; Top-1 8/8; Top-3 8/8; clear 5; ambiguous 2; correct-but-low 1; incorrect rankings 0. Detailed source pages, candidate paths, scores and ranks are in `siglip_real_smoke.json/md` and `siglip_calibration.md`.

All 247 prior ranking opportunities were runnable locally (152 candidate groups). Failures: 0. Candidate confidence: HIGH 9; ambiguous 147; low relevance 91. Group confidence: HIGH 9; ambiguous 99; low 44. HIGH plus new strong source evidence: 0; new automatic image resolutions: 0.

Fresh opportunity pass: 6.66s load; 166.74s candidate processing; 212.49s total; 0.675s/candidate; 1288MB peak working set. It ran 239 fresh predictions and reused eight scores. The later check reused all 247 score entries, taking 47.69s total (including release scanning and duplicate validation). Model weights were not downloaded again.

## C. Cloud avoidance

Actual live Groq calls: 0; Gemini: 0; paid: 0. Eight candidate groups are already resolved by existing verification/source evidence. 144 groups remain candidates for Groq assurance; these are routing requirements, not 144 measured provider requests. Gemini need is unknown until Groq availability/ambiguity is observed. 350 missing-image tasks have no usable cached candidate; they belong to research, not image inference. This is cached availability, not a fresh web search.

Incremental measured cloud-call savings attributable to SigLIP: **0**. Nine decisive rankings alone do not prove POI identity; none qualified for additional safe automatic acceptance. Existing deterministic P18 acceptance already skipped cloud. Source contradictions are rejected before ranking; fallback and FREE_ONLY policies remain strict.

## D/E. Priority model and reduction

| City | Before | P0 | P1 | P2 | P3 | P4 | No research | Default | Reduction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Jaipur | 771 | 53 | 1 | 56 | 281 | 269 | 111 | 110 | 85.73% |
| Udaipur | 264 | 55 | 1 | 53 | 61 | 58 | 36 | 109 | 58.71% |
| Varanasi | 471 | 112 | 0 | 92 | 49 | 118 | 100 | 204 | 56.69% |
| Manali | 131 | 14 | 7 | 15 | 39 | 42 | 14 | 36 | 72.52% |

Total: 1,637 → 459 actionable tasks, a 71.96% reduction. Default is P0/P1/P2; --all includes P3/P4; DO_NOT_RESEARCH stays internal. Stable IDs and priority/tier/relevance/prominence/category/place/type order survive batching.

## F. Jaipur Batch 1

75 tasks: 50 REAL_PRIMARY_IMAGE, 4 COORDINATE_RESEARCH, 15 OPENING_HOURS, 1 DESCRIPTION, 5 WEBSITE, 0 IDENTITY_RESEARCH. P0 53, P1 1, P2 21. All 50 required-photo tasks are included; 35 other actionable tasks remain beyond this cap.

Exact files:

- `C:\Users\girir\Documents\YatraCanvas-DataFactory\data\research\exports\jaipur\batch_1\research_handoff.json`
- `C:\Users\girir\Documents\YatraCanvas-DataFactory\data\research\exports\jaipur\batch_1\research_handoff.md`
- Focused required-image handoff (50 tasks): `C:\Users\girir\Documents\YatraCanvas-DataFactory\data\research\exports\jaipur\required_images\research_handoff.md`
- Focused core-hours handoff (24 tasks): `C:\Users\girir\Documents\YatraCanvas-DataFactory\data\research\exports\jaipur\core_hours\research_handoff.md`

Each directory includes JSON, Markdown, CSV, exact results template, strict JSON Schema and a separate internal inventory.

## G. Safe round trip

`python -m scripts.verify_research_roundtrip` generated an isolated synthetic release and handoff, validated registered task/place IDs through CLI `research-import --dry-run` (exit 0), then CLI `research-import --apply` (exit 0). The explicit fixture router replaces cloud. Hours syntax, source retention, legal metadata/file/duplicate/local-media checks and established assurance all ran. Apply performed the full JSON/JSONL/Parquet/SQLite/media/checksum offline rebuild; release validation passed. Only opening_hours and images changed; two provenance rows were stored; the original fixture v3 was preserved.

Fixture readiness changed from general 0%/required coverage 0%/not ready to 100%/100%/ready. This is fixture evidence only; no synthetic fact, license or source result was applied to production. See `research_roundtrip.json/md` for exact fixture paths and decisions.

## H. Commands and tests

```powershell
python -m datafactory.cli local-ai-status --download
$env:HF_HUB_OFFLINE = '1'
python -m datafactory.cli local-ai-status
python -m datafactory.cli local-ai-smoke --fixture tests/fixtures/siglip_real_cases.json --refresh-scores --output reports/local_intelligence/siglip_real_smoke
python -m datafactory.cli local-ai-smoke --output reports/local_intelligence/siglip_opportunities
python -m datafactory.cli local-ai-smoke --output reports/local_intelligence/siglip_opportunities_final
python -m scripts.report_research_optimization
python -m scripts.verify_research_roundtrip
python -m pytest -q --basetemp scratch/pytest-optimization-final-review -o cache_dir=scratch/pytest-cache --tb=short
python -m pip check
```

Commands above used the project interpreter `.\venv\Scripts\python.exe` (not the system interpreter).

Actual final pytest output:
```
........................................................................ [ 32%]
........................................................................ [ 65%]
........................................................................ [ 98%]
...                                                                      [100%]
219 passed in 30.92s
```

pip check: no broken requirements. Normal tests disable real model loads; opt-in smoke uses actual cached weights. Earlier test setup failed on the host shared temp-directory ACL; workspace --basetemp resolves it. Dependency versions: torch 2.14.1+cpu, transformers 4.57.6, sentencepiece 0.2.2, protobuf 6.33.6.

## I. Readiness and limits

| City | General usability | Required media coverage | Source ready | Original v3 preserved |
|---|---:|---:|---|---|
| Jaipur | 1.17% | 3.85% | False | True |
| Udaipur | 0.93% | 1.82% | False | True |
| Varanasi | 2.87% | 4.27% | False | True |
| Manali | 0.06% | 0.0% | False | True |

Required coverage now counts renderable, legally attributed, verified real media. Source readiness still requires >=95% general usability, 100% required coverage and all critical gates. Existing app fallbacks are not bundled source photographs and cannot inflate either metric. Production packs remain source-unready; this pass provides prioritization and validated local tooling, not new external source data.

Calibration is provisional and derived from eight selected cases, not a universal or held-out accuracy threshold. Top-3 is weak with three candidates. No qualifying cached food/cafe group was available. Real inference is proven, but wider identity calibration remains future work. Gemini demand cannot be measured without cloud responses, and no free quota was spent just to populate a report. Model downloads needed network escalation; later inference and health ran offline. Production release and original v3 snapshots remain unchanged across all four cities. No City Lab files, paid API, vector DB, local LLM or new provider were introduced.

Review skill: user requirements served as the benchmark. Scope/pipeline boundaries and strict import safety passed review. Remaining dataset-readiness and statistical-calibration limits are reported above; no critical implementation defect was found in the checked paths.
