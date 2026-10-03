# Local intelligence + research handoff — delivery report

3 October 2026. Implemented against existing DataFactory interfaces. No City Lab
changes, production research application, fresh extraction or live cloud inference.

## Architecture Audit

Reused the existing FREE_ONLY router and AI decision/cache schemas, source evidence
index, license/CDN/file gates, media downloader and WebP processor, repair decisions,
human curation locks, regional policy, fallback policy, usability and transactional
JSON/JSONL/Parquet/SQLite/offline exporters. Original v3 packs remain preserved.

Added `datafactory/local_intelligence/` adapters for bounded optional models,
perceptual duplicate checks and mature schedule validation. Extended identity and
geographic assurance. Added `datafactory/research/` typed result schemas, unresolved
task selection, export registry, public companions, source quality inference and
validated immutable imports. Repair now emits research tasks, while the CLI provides
`research-export` and `research-import`.

See [architecture note](../docs/local-research-architecture.md) and
[workflow/dependency details](../docs/local-research-workflow.md).

## Dependencies Added

| Dependency | Version/range | License | Purpose/selection |
|---|---|---|---|
| ImageHash | 4.3.2 installed | BSD-2-Clause | Established pHash/dHash/colorhash; avoids imagededup/OpenCV setup. |
| opening-hours-py | 2.1.4 installed | MIT OR Apache-2.0 | Mature OSM parser, Windows Python 3.12 compatible wheel; avoids mandatory npm. |
| SciPy, transitive | 1.18.1 installed | BSD-3-Clause, distribution retains bundled licenses | ImageHash transforms; binary wheel setup verified. |
| PyWavelets, transitive | 1.10.0 installed | MIT AND BSD-3-Clause | ImageHash dependency; binary wheel setup verified. |
| opening_hours, optional npm | 3.14.0 declared | LGPL-3.0-only | Preferred JS parser adapter; Node/npm integration remains optional. |
| torch, optional | >=2.2,<3 | BSD-3-Clause | Local CPU inference. |
| transformers, optional | >=4.45,<5 | Apache-2.0 | Configurable SigLIP model/processor, normal local/HF cache. |
| sentence-transformers, optional | >=3,<6 | Apache-2.0 | Lightweight supporting sentence embeddings. |
| sentencepiece, optional | >=0.2,<1 | Apache-2.0 | SigLIP tokenizer support. |

RapidFuzz 3.14.6 and Shapely 2.1.2 were already installed and were reused. Python
dependencies passed `pip check`. Optional model packages/weights were deliberately
not installed. JS adapter availability is reported safely when its package is absent.

Maintenance/compatibility/license references:
[ImageHash](https://pypi.org/project/ImageHash/),
[opening-hours-py](https://pypi.org/project/opening_hours_py/),
[opening_hours.js metadata](https://github.com/opening-hours/opening_hours.js/blob/main/package.json),
[PyTorch](https://pypi.org/project/torch/),
[Transformers](https://pypi.org/project/transformers/),
[Sentence Transformers](https://pypi.org/project/sentence-transformers/),
[SentencePiece](https://pypi.org/project/sentencepiece/).

## SigLIP

Configured model: `google/siglip-base-patch16-224`, CPU, cache-only by default,
four candidates per batch, at most 20 candidates, 384px analysis copies. Model ID,
revision, limits and conservative thresholds are configurable. Rankings are cached
against image bytes, model/revision and POI/city prompts. The standard model cache
is reused; missing packages/weights disable ranking for that run without crashing.
Model scores never prove identity. Correct QID/P18/Commons evidence can skip AI.
Source download budgets remain independent of inference budgets.

Actual cached-snapshot ranking opportunities: Jaipur 83, Udaipur 64, Varanasi 89,
Manali 11 — **247** candidates. Actual SigLIP rankings/batches: **0**, because the
model stack/weights are absent. Each city exercised one model-unavailable fallback.
Mocks verified ordering, batches, maximum candidates, image limits, disk cache hits,
city separation, high/low confidence and non-photo review behavior.
Default SigLIP weights are Apache-2.0. [Model card](https://huggingface.co/google/siglip-base-patch16-224).

## Duplicate Detection

SHA comparison runs first. Established ImageHash methods run for byte variants;
combined spatial/color/aspect guards avoid over-aggressive matching. Candidate
pools are scoped to a POI; imports also compare against its existing photos.

| City | Valid cached files | Duplicate candidates | Remaining ranking opportunities |
|---|---:|---:|---:|
| Jaipur | 102 | 19 | 83 |
| Udaipur | 79 | 15 | 64 |
| Varanasi | 101 | 12 | 89 |
| Manali | 11 | 0 | 11 |

**46 duplicates** found in cached candidate analysis; no production asset was
deleted. Tests cover exact, re-encoded, resized and distinct/low-information images.

## Entity/Text Similarity

Reuse normalized RapidFuzz names and aliases; source ID/name/category/coordinate
agreement can resolve locally before the router. Optional MiniLM embeddings are
supporting evidence with bounded text and lazy cached model loading. Cross-city
identity remains isolated. A high semantic score alone cannot merge an entity.
Published-ID migrations still require review. Default sentence model:
`sentence-transformers/all-MiniLM-L6-v2` (Apache-2.0).
[Model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).

## Geography

Municipal and travel-region Shapely containment/distance/buffer evidence extends
existing haversine source-coordinate corroboration. Outside a municipal polygon
does not imply invalidity. Destination association and independent source IDs
remain required for accepted outlying regions or coordinate repair. Geometry
failures become reviewable. Tests include inside, nearby accepted travel region,
far away, two independent agreeing sources and a single source. Export selected
14 coordinate research tasks across the four current snapshots.

## Hours Validator

The mature Python OSM parser is installed and exercised. The opening_hours.js
adapter is configurable, with a five-second JSON stdin bridge and conservative
warning handling. Neither path silently rewrites broken source schedules.
Split shifts/closed days/24/7/invalid syntax are covered. Imported schedules require
source metadata, fresh timestamps and exact source support; conflicting day/time
mappings remain REVIEW. Source prose uses the existing bounded extractor on apply,
while dry-run reports required extraction. No source evidence means unresolved.

Actual locally parser-valid existing schedule strings: Jaipur 62, Udaipur 27,
Varanasi 23, Manali 12 — **124**. Syntax validity does not imply verified freshness
or factual accuracy, so appropriate research tasks remain.

## Research Export

JSON is canonical; Markdown contains current-web/no-guess/licensing instructions.
CSV, a strict result JSON Schema and an UNRESOLVED result template are companions.
Task/place IDs and city/state/country are explicit. Ordinary fallback-eligible cafes
and restaurants do not produce metadata tasks unless optional research is requested.

| City | OPENING_HOURS | REAL_PRIMARY_IMAGE | WEBSITE | DESCRIPTION | COORDINATE_RESEARCH | IDENTITY_RESEARCH | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| Jaipur | 236 | 230 | 100 | 201 | 4 | 0 | 771 |
| Udaipur | 90 | 89 | 38 | 45 | 2 | 0 | 264 |
| Varanasi | 151 | 146 | 111 | 63 | 0 | 0 | 471 |
| Manali | 43 | 29 | 15 | 36 | 8 | 0 | 131 |

**1,637 unresolved tasks**. Current published snapshots have no unresolved
identity blockers selected; historical quarantined collisions are not revived or
matched by name. Identity task generation/import review is exercised with fixtures.

Outputs are under `data/research/exports/india/<state>/<city>/`. See
[machine report](local_research_acceptance.json) and [city report](local_research_acceptance.md).

## Research Import

Fixtures demonstrate source-backed valid hours, invalid/conflicting/stale schedules,
unknown place IDs, wrong task IDs, strict schema rejection, missing sources, claimed
quality rejection, locks, snapshot changes, partial/unresolved/conflicting results,
manual image legal/path/source/duplicate/wrong-place checks, established WebP
processing, complete pack validation, audit history and repeat-import no-ops.
Dry-run immutability and failed-publication preservation are tested.

Safe apply publishes a complete new offline pack before updating the history/head.
The pack includes the import audit so an interrupted index write can be recovered.
No real external research file was available; no external result was fabricated or
applied to production. The actual Jaipur UNRESOLVED template dry run matched all
**771** task IDs with **0** applies, rejects, downloads or cloud calls.

## Jaipur

All **50** unresolved REAL_REQUIRED photos are P0 tasks. **23** have no saved
discovered candidates and immediately become handoffs, including Ajmeri Gate,
Alice Garg Seashell Museum, Chulgiri Digamber Jain Temple and EleJungle. Stable IDs
are generated generically; no city/place ID is hardcoded in production behavior.
Absent historical IDs remain absent. No SigLIP or image-verification request occurs
when discovery is empty.

## Multi-City

The same commands and import registry operate in Jaipur, Udaipur, Varanasi and
Manali. Required photos with no saved discovered candidate: **23 / 28 / 70 / 13**.
Original v3 and selected app-fallback snapshot hashes stayed unchanged in all four
analyses. Each task retains state/country context and stable city-scoped identity.

## AI Usage

Actual acceptance analysis: **0 Groq, 0 Gemini, 0 paid calls**, 1,637 handoff tasks.
Actual live model-based resolutions: **0**. Syntax checks and duplicate analysis
were local. Three Varanasi cached candidates satisfy entity-linked acceptance
conditions; this is an opportunity, not a newly applied research resolution.
Measured cloud call reduction is **0** because no new live inference baseline was
run. The implementation reports real per-provider calls, local acceptance and
potential checks; tests demonstrate skips without inventing monetary savings.

## Tests

Final complete suite:

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=scratch/local-research-final-delivery --tb=short
```

**197 passed in 30.35 seconds.** Default tests block live HTTP and mock local models.
Final source-text/import follow-up: **25 passed in 5.82 seconds**, including qualified
24/7 prose that must remain reviewable rather than becoming an unconditional schedule.
Focused final signature/media/source suite: **86 passed in 7.67 seconds**.
`python -m pip check`: **No broken requirements found**.
Changed tracked source/config/docs files passed `git diff --check` (Git printed only
its existing Windows line-ending notice). Untracked new modules are exercised by
the complete suite.

Actual CLI/script commands:

```powershell
.venv/Scripts/python.exe -m datafactory.cli research-export --cities Jaipur,Udaipur,Varanasi,Manali --all
.venv/Scripts/python.exe -m scripts.report_local_research
.venv/Scripts/python.exe -m datafactory.cli research-import --file data/research/exports/india/rajasthan/jaipur/research_results.template.json --dry-run
```

## Remaining Limitations

- Real SigLIP/Sentence Transformers inference was not exercised; install optional
  packages and prepare model weights explicitly to activate it. Normal tests never
  require those downloads.
- JS hours adapter is implemented but not live-exercised because npm/parser are
  absent; the installed mature Python parser is the verified default.
- Original-source automatic media license verification still supports Commons.
  Other supplied image providers remain REVIEW even when a local file exists.
- Perceptual thresholds are conservative; major crops or changed viewpoints may
  not deduplicate. Polygon nearest-point distances are local approximations.
- Source quality is derived evidence policy, not proof of a page's truth. Research
  must supply accurate quotations and current timestamps.
- Existing identity migrations/quarantined candidate decisions and destination
  curation remain in the existing human review workflow, with City Lab untouched.
- Historical release selection deliberately reopens historical unresolved data;
  normal export follows the latest research head. A new handoff is required after
  another import so stale batches cannot discard newer research.
