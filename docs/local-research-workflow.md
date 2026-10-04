# Local intelligence and research handoff

DataFactory uses deterministic/local evidence before the existing free-only Groq
then Gemini router. Missing important external evidence becomes a research task:
empty discovery has no image to inspect; absent source hours cannot be inferred
from model memory. ChatGPT Web or a human researches exported tasks and returns
structured results. No new paid API, OpenAI API, local LLM or backend service.
City Lab remains outside this workflow.

## Local intelligence

- **SigLIP:** optional local image/text ranking, entity/city/category prompts and
  conservative photo/map/diagram/logo/poster/document/interior/exterior labels.
  Weak labels never reject candidates. Strong non-photo labels send contextual
  candidates to review. Authoritative P18 identity evidence outranks similarity.
  Scores alone never verify a POI. Defaults: 20 candidates, batches of four,
  analysis copies at most 384px, CPU. Unavailable models skip local ranking and
  preserve existing assurance/cloud processing.
- **Duplicates:** SHA first, then established ImageHash pHash/dHash/colorhash with
  aspect and low-information guards. Detects encoding, resize and some minor crop
  variants without collapsing similar buildings. Scope is a POI's candidate pool.
  Major crops/viewpoint changes can remain distinct.
- **Text:** reuse RapidFuzz normalization and aliases. Optional MiniLM embeddings
  support ambiguous comparisons. Matching source IDs, category, coordinates and
  name can skip AI. Embeddings alone never merge entities; published-ID changes
  remain review-only.
- **Geometry:** Shapely municipal/regional polygons, buffer evidence and distances.
  Distances use lon/lat nearest points plus haversine, suitable for local travel
  regions rather than a global geodesic polygon engine. Outside municipality can
  still be valid with destination association and accepted regional evidence.
- **Hours:** mature OSM parser replaces the prior regex subset. Split shifts,
  closed days, 24/7 and valid overnight schedules retain source syntax. Unavailable
  parsers block auto-apply. Source schedule conflicts remain in review; prose uses
  existing bounded source extraction on apply. Dry runs never call AI.

### Setup and cache

Normal `pip install -e .` installs deterministic tooling. Optional model setup:

```powershell
python -m pip install -e '.[local-models]'
```

First use may download model weights only when `LOCAL_MEDIA_ALLOW_DOWNLOAD=true`
or `LOCAL_TEXT_ALLOW_DOWNLOAD=true`. SigLIP uses `data/cache/models` by default;
`LOCAL_MEDIA_MODEL_CACHE` overrides that path. Later runs are cache-only. The checked
revision is pinned in `config/local_media.yaml`; environment overrides remain supported.
SigLIP base has about 200M parameters: allow roughly 1GB for weights plus runtime
overhead. Default tests require neither model weights nor the optional ML packages.

See `.env.example` for model/revision, enable flags, device, batch/candidate/thumbnail
limits, conservative thresholds, duplicate threshold, hours backend and
`HOURS_RESEARCH_MAX_AGE_DAYS` (default 180). Text embeddings default disabled.

The default Python hours parser avoids mandatory Node/npm setup. Where npm is
installed, the preferred JS parser is also supported:

```powershell
npm install --ignore-scripts
$env:HOURS_VALIDATOR_BACKEND = 'javascript'
```

The bridge uses JSON stdin and a bounded Node subprocess; parser warnings require
review. There is no custom schedule grammar fallback.

### Dependencies

| Dependency | Version/range | License | Purpose and choice |
|---|---|---|---|
| ImageHash | 4.3.2 | BSD-2-Clause | Established hashes; simpler than imagededup/OpenCV; Python plus NumPy/SciPy/PyWavelets wheels. |
| opening-hours-py | 2.1.4 | MIT OR Apache-2.0 | Mature Rust OSM grammar, Windows CPython 3.10 ABI wheel works with Python 3.12; avoids mandatory npm. |
| SciPy (ImageHash dependency) | installed 1.18.1 | BSD-3-Clause; bundled components retain their licenses | Numerical transforms for pHash; Windows wheel avoids a compiler setup. |
| PyWavelets (ImageHash dependency) | installed 1.10.0 | MIT AND BSD-3-Clause | ImageHash's wavelet dependency; Windows wheel installation was verified. |
| opening_hours (optional npm) | 3.14.0 | LGPL-3.0-only | Established OSM JS parser; subprocess isolation; Node >=14. |
| torch (optional) | >=2.2,<3 | BSD-3-Clause | Local CPU model runtime; resolve wheels against supported Python. |
| transformers (optional) | >=4.45,<5 | Apache-2.0 | SigLIP AutoModel/AutoProcessor, HF cache, safetensors, no remote code. |
| sentence-transformers (optional) | >=3,<6 | Apache-2.0 | Lightweight embeddings sharing the optional model runtime. |
| sentencepiece (optional) | >=0.2,<1 | Apache-2.0 | SigLIP tokenizer. |

RapidFuzz and Shapely were already dependencies. ImageHash 4.3.2 and
opening-hours-py 2.1.4 installs were exercised on Windows Python 3.12. The optional
ML stack has now been installed and exercised locally. Protobuf is required by the
SigLIP tokenizer (`protobuf>=4,<7` is included in the optional extra). Normal tests
still require no model download. No FAISS, vector database or new service.

Primary references for maintenance, compatibility and license checks:
[ImageHash](https://pypi.org/project/ImageHash/),
[opening-hours-py](https://pypi.org/project/opening_hours_py/),
[opening_hours.js](https://github.com/opening-hours/opening_hours.js),
[SigLIP model card](https://huggingface.co/google/siglip-base-patch16-224),
[Sentence Transformers installation](https://www.sbert.net/docs/installation.html).
Optional package metadata was also checked for
[PyTorch](https://pypi.org/project/torch/),
[Transformers](https://pypi.org/project/transformers/),
[Sentence Transformers](https://pypi.org/project/sentence-transformers/) and
[SentencePiece](https://pypi.org/project/sentencepiece/).
Default model licenses are Apache-2.0; check a replacement model's license separately.

## Research export

```powershell
python -m datafactory.cli research-export --city Jaipur --priority P0,P1,P2 --limit 75
python -m datafactory.cli research-export --city Jaipur --type REAL_PRIMARY_IMAGE --priority P0
python -m datafactory.cli research-export --city Jaipur --type OPENING_HOURS --priority P2
python -m datafactory.cli research-export --cities Jaipur,Udaipur,Varanasi,Manali
python -m datafactory.cli research-export --city Jaipur --all
```

Default source is the latest research-imported head, then `v3-app-fallbacks`, then
`v3`. `--version` chooses an explicit snapshot. Same-name cities require state/country
disambiguation. Default export includes only P0/P1/P2. `--all` (or legacy
`--include-optional`) opts into P3/P4, but never DO_NOT_RESEARCH. Explicit priorities
override the default. Types, priorities and a positive limit combine; ordering is
priority, tier, travel relevance, prominence, category importance, place ID and type.
Limits do not change task IDs. A repeated identical batch remains identical; select
another filter or import completed work and re-export to advance the queue.

`research_worthiness` is deterministic and field-specific. Required real photos are
always P0. Important unresolved identity/coordinate conflicts are P0/P1. Core venue
hours are P2 when scheduling matters; recommended venue hours are normally P3.
Generic urban parks, viewpoints and open landmarks without venue evidence do not
require hours research. Missing descriptions prioritize important attractions;
websites prioritize useful visit-planning evidence. Ordinary optional metadata is
P4; support metadata and fallback-allowed photo gaps are DO_NOT_RESEARCH.
Named museums/temples/forts/palaces/gardens also establish scheduling relevance when
the existing category is generic heritage; they never establish an actual schedule.

Outputs under `data/research/exports/<country>/<state>/<city>/`:

- `research_handoff.json`: canonical tasks, stable IDs, explicit city/place context,
  reduced public evidence and explainable priority.
- `research_handoff.md`: ChatGPT-ready instructions and task context.
- `research_handoff.csv`: optional spreadsheet review; not an import format.
- `research_results.schema.json`: strict typed payloads, no researcher confidence.
- `research_results.template.json`: UNRESOLVED entries ready to fill.
- `research_inventory.json`: all candidate gaps, including P3/P4 and suppressed
  tasks with `why_not_research`. This is for internal audit; do not upload it as the
  normal handoff. `reason_codes` and `why_research` explain exported work.

Types: OPENING_HOURS, REAL_PRIMARY_IMAGE, WEBSITE, DESCRIPTION, COORDINATE_RESEARCH,
IDENTITY_RESEARCH. Future types extend the enum/schema/selector/validator, leaving
the interchange intact. Priority: P0 critical required photographs/identity/coordinate
conflicts; P1 important conflicts/prominent preferred media; P2 important hours,
descriptions and useful websites; P3 useful later research; P4 optional metadata.

Upload the Markdown/JSON/schema to ChatGPT Web. Request current source research
and a completed template. Save `research_results.json`, preserving handoff_id,
task_id and place_id. Statuses are FOUND, PARTIAL, UNRESOLVED, CONFLICT; only validated
FOUND entries can auto-apply. Do not calculate confidence or change IDs.

## Research import and rebuild

```powershell
python -m datafactory.cli research-import --file research_results.json --dry-run
python -m datafactory.cli research-import --file research_results.json --apply
```

Dry run is read-only: no file/pack/audit/cache writes, downloads or cloud calls.
It reports supplied/matched/valid/auto-applicable/review/rejected/missing POIs,
invalid sources/schedules and media requiring verification. Actual source/image
verification may be needed on apply; dry-run REVIEW never waives licensing.

Add `--network` on apply to retrieve approved original-source metadata and images.
Arbitrary image hosts are not downloaded. The existing CDN allowlist, redirect,
size and MIME protections remain. Commons metadata independently verifies original
creator/license. Unsupported original providers remain REVIEW.

Manual files use explicit result-relative mappings:

```text
research_import/
  research_results.json
  images/garden.jpg
```

The image payload supplies `local_file: "images/garden.jpg"`, source_page_url,
direct_media_url, source_provider, creator, license, license_url and attribution.
Filename never identifies a POI. Manual images still undergo file/legal/duplicate/
local relevance/existing cloud identity assurance before established WebP processing.
Missing files, unsafe paths, unsupported sources and wrong images cannot auto-apply.

Source quality is inferred from URL/provider/existing identifiers, ignoring claimed
quality. Known official/government hosts and entity-matched structured sources are
stronger than curated/secondary/unknown sources. Hours require valid syntax, fresh
timestamps and exact source support; prose uses bounded extraction where necessary.
Coordinate repair still requires two independent identity-matched source points
and an accepted travel region. Human curation locks remain authoritative.

Apply checks registered IDs, city and original snapshot hashes, stages safe changes
and publishes a complete immutable offline pack via the existing JSON/JSONL/Parquet/
SQLite/media exporter. Default is `v3-research`, or a unique suffix if occupied.
Safe apply already rebuilds every projection and validates before publication, so
no extra `--rebuild` is needed. Failure leaves source release and head untouched.
A shared import lock prevents concurrent divergent imports. After a killed process,
remove only the empty `data/research/.import-lock` once no import remains running.

The pack contains `research_import.json`; history is under `data/research/imports/`.
Audit includes input hash/date/task/place IDs/decisions/provenance. Re-import recovers
a published audit if an auxiliary index write was interrupted. Identical previously
applied input is a no-op. Export a fresh handoff after another successful import;
an older handoff cannot overwrite newer research.

Future export follows the research head and omits solved fields. Stale hours return
RECHECK_RECOMMENDED without deletion. Images do not have arbitrary expiry; missing
or invalid files and changed identity evidence re-enable tasks. `--version v3`
deliberately re-examines historical data. Subsequent repair uses the returned pack:

```powershell
python -m datafactory.cli repair --city Jaipur --state Rajasthan --version v3-research --apply --output-version v3-research-assured
```

Use the exact returned version if a suffix was allocated. Legacy
`build-offline --from-release` starts from original v3; research apply already
rebuilt the complete pack and does not need that extra step.

## Privacy, testing and limits

Export only public POI/source information. No environment values, API keys, private
curator notes or secret-bearing/query URLs. Source quality is an evidence policy,
not independent proof of a public page's truth. Researchers must provide accurate
quotes and timestamps. No external research results are fabricated by tests.
Published-ID tasks do not revive upstream quarantined candidates or match by name.

```powershell
python -m scripts.report_research_optimization
python -m scripts.verify_research_roundtrip
python -m pytest -q -p no:cacheprovider --basetemp=scratch/local-research-verification
```

The report measures cached local/model/cloud counts, without monetary claims or
invented savings. Optional real model integration is separate from default tests.

## Real model diagnostics and measured calibration

```powershell
python -m datafactory.cli local-ai-status --download  # first preparation only
$env:HF_HUB_OFFLINE = '1'
python -m datafactory.cli local-ai-status             # cached weights, no cloud
python -m datafactory.cli local-ai-smoke --fixture tests/fixtures/siglip_real_cases.json --refresh-scores --output reports/local_intelligence/siglip_real_smoke
python -m datafactory.cli local-ai-smoke --output reports/local_intelligence/siglip_opportunities
```

The health command reports load/inference, device/cache, duplicates, fuzzy text,
geometry and hours validation. Disabled optional semantic text is shown explicitly.
`local-ai-smoke` is opt-in, performs actual inference on cached candidate files, and
never invokes Groq/Gemini. `--refresh-scores` bypasses score caches while reusing model
weights; without it, score caches are reused. Normal pytest runs disable model loads;
`RUN_LOCAL_MODEL_TESTS=1` allows them, but the smoke command is the reproducible real
integration check. Never enable automatic downloads in ordinary tests.

The eight reference cases and provisional thresholds are documented in
`reports/local_intelligence/siglip_calibration.md`. Scores are similarity evidence,
not identity probabilities. LOW is a review route, not image rejection. Unavailable
or ambiguous local ranking preserves existing cloud assurance. Deterministic P18
evidence can already accept without cloud; contradictory entity IDs are rejected
before either local scores or cloud can override them. A high SigLIP score alone
never accepts an image. The existing router stops after a decisive Groq answer;
Gemini is used for unavailable/rate-limited Groq or important ambiguity.

## Practical sequence

1. Build or repair a city; deterministic filters, duplicates and source evidence run first.
2. Local SigLIP ranks available candidates. Strong identity evidence resolves safe
   media locally; cloud assurance runs only where necessary. Empty discovery goes to handoff.
3. Export P0/P1/P2 with `--limit 75`; upload the Markdown, JSON and schema to ChatGPT Web.
4. Save the returned `research_results.json`; run import `--dry-run`, then `--apply`.
5. Apply rebuilds JSON/JSONL/Parquet/SQLite/media and recalculates usability, required
   media coverage, critical blockers and source readiness atomically in a new pack.
6. Review both `GENERAL_USABILITY` (target >=95%) and `REAL_REQUIRED_MEDIA_COVERAGE`
   (target 100%); source readiness also requires all other critical gates.
7. Re-export remaining research. Sync the improved pack to City Lab later; this
   phase does not modify City Lab.

Generated Jaipur batches are under `data/research/exports/jaipur/`: `batch_1/`,
`required_images/` and `core_hours/`. Round-trip artifacts live in an explicitly
synthetic `scratch/fixture-roundtrip-*` workspace. No real schedule or license is
invented or applied to production to demonstrate that workflow.

## Research media recovery and fresh retries

Research adds verified Commons metadata to existing source evidence. Known CC/CC0
names and Creative Commons legal URLs use a finite canonical mapping; only known
CC HTTP URLs upgrade to HTTPS. Creator comparisons use NFC, preserving meaningful
characters. Commons filenames decode once and retain punctuation and Unicode.
Different licenses, creators or original sources stay in review.

An exact Commons source plus perceptual confirmation, or exact local bytes, can
identify an existing primary/gallery asset for the same POI. Reuse still requires
current deterministic checks and independent identity assurance. Existing verified
identity must match the current POI digest and primary file signature. Verified
metadata conflicts, unrelated gallery duplicates and cross-POI duplicates remain
blocked. Reuse copies original WebP bytes into the new pack and upgrades provenance.

Actual Wikidata entity claims can restore `wikidata_p18` only when the POI QID and
P18 Commons filename both match. Filename similarity cannot establish that link.
Other known source methods survive exact source matches. Verified reuse and P18
run before local SigLIP and cloud routing; SigLIP alone never accepts an image.
Groq/Gemini retain the existing FREE_ONLY gates, budgets and assurance thresholds.
Failures record category, HTTP status, error class, retryability and timestamp,
without response bodies, authorization headers or API keys.

Confirmed MPO files have only their primary frame normalized to bounded RGB WebP
before normal validation. The 20 MB input and 40 million pixel budgets still apply;
corrupt frames reject. Oversized verified Commons originals may use API-provided
derivatives with `media.commons_derivative_long_edge` (default 1920; bounded to
1600–2400). `media.commons_max_download_bytes` cannot exceed 20,000,000. Downloaded
dimensions must match Commons metadata. Derivatives may use only the exact
`upload.wikimedia.org` or `thumb.wikimedia.org` hosts and the Commons thumbnail
path; redirects and unrelated hosts stay blocked. Original file, source page, creator and
license remain the provenance; the derivative URL is only the fetched representation.

After a successful import, export remaining required images from the current head:

```powershell
.\.venv\Scripts\python.exe -m datafactory.cli research-export --city Jaipur --state Rajasthan --type REAL_PRIMARY_IMAGE --priority P0 --output data/research/exports/jaipur/required_images_retry
.\.venv\Scripts\python.exe -m datafactory.cli research-retry --previous-file data/research/import_inputs/jaipur_image_research_results.json --handoff-id <fresh-registered-id> --output data/research/import_inputs/jaipur_image_retry_results.json
.\.venv\Scripts\python.exe -m datafactory.cli research-import --file data/research/import_inputs/jaipur_image_retry_results.json --dry-run
.\.venv\Scripts\python.exe -m datafactory.cli research-import --file data/research/import_inputs/jaipur_image_retry_results.json --apply --network --output-version v3-research-jaipur-images-02
```

`research-retry` verifies both registered snapshots and maps evidence only when
place identity, task type and unresolved condition are unchanged. IDs come from
the new registry. The mapping report classifies retryable evidence, new research,
genuine conflict and unresolved sources. PARTIAL/CONFLICT/UNRESOLVED remain so;
changed identity receives an unresolved request for new research. Original bundles,
source packs and human curation remain unchanged. Import retains all existing
snapshot, stale-head, license, media, transaction and offline publication gates.

## Required-media resolution queues

`research-export` now sends only media needing external evidence to web research.
It uses deterministic registered import history and current assurance records;
it never invokes a model to decide a queue. Required media remains in the inventory
while temporary provider holds and identity reviews are excluded from the web handoff.

```powershell
.\.venv\Scripts\python.exe -m datafactory.cli research-queues --city Jaipur --state Rajasthan --output data/research/exports/jaipur/required_images_remaining
```

The command follows the unchanged latest research head and creates three queues:

- `PROVIDER_RETRY` / `ASSURANCE_HOLD`: existing researched candidate, matching
  verified legal/source metadata, successful download or reuse, passed deterministic
  checks and a provider availability blocker. HTTP 429/503 never creates a research gap.
- `NEW_RESEARCH_REQUIRED` / `RESEARCH_GAP`: unresolved/insufficient evidence, wrong
  candidate or poor identity/composition. Tasks include prior public findings, source
  URLs, identifiers, aliases, coordinates and explicit alternate-photo instructions.
- `MANUAL_REVIEW` / `IDENTITY_REVIEW`: structured identity blockers or explicit
  research findings requiring identity/policy judgment before an image search. A valid
  candidate with incomplete internal assurance also remains in manual assurance review.

Mobile-card suitability failures request a different composition, retain previous
source exclusions and prioritize recognizable subjects with useful card framing.
Observatory and park context adds instrument/park-specific guidance. Prior research
notes and earlier source pages explain licensing and wrong-subject dead ends.
Generic activity imagery never proves a specific operator, venue or listing.
Unresolved generic activity names without an independently identified entity require
manual identity/policy review. `MEDIA_POLICY_REVIEW_RECOMMENDED` is advisory: exports
never change REAL_REQUIRED, published identities or assurance thresholds. A named,
identified commercial venue can remain in exact-venue research with a policy flag.

`status_report.md/json` inventories every remaining task. `new_research/` contains a
registered ChatGPT-ready handoff, unchanged result schema and template. `manual_review/`
contains public review context. `provider_retry/retry_tasks.json/md` retains candidate,
legal/source evidence, deterministic checks, local SigLIP assessment, previous decisions,
safe provider diagnostics and timestamps. Provider failure counts describe affected
records and can overlap; shared router cooldown diagnostics do not imply one HTTP
attempt per POI. Exact pending-assessment timestamps are recovered from matching cache
entries where available; otherwise unknown timestamps remain null.

Provider retries use the existing importer, without adding discovery or a retry service:

```powershell
.\.venv\Scripts\python.exe -m datafactory.cli research-import --file data/research/exports/jaipur/required_images_remaining/provider_retry/research_results.retry.json --dry-run
# Later, when a controlled provider retry is authorized and availability permits:
.\.venv\Scripts\python.exe -m datafactory.cli research-import --file data/research/exports/jaipur/required_images_remaining/provider_retry/research_results.retry.json --apply --network --output-version v3-research-provider-retry-01
```

The retry bundle is registered against the current source snapshot, preserves valid
research and copies bounded local input files when needed. If an original input moved
outside `data/research/import_inputs`, public candidate fields and source excerpts can
be restored from its registered import receipt. This creates no new research claims.
Unarchived or unsupported evidence with insufficient assurance stays manual rather
than being treated as a provider-ready result.

Actual apply retains deterministic checks, cache/SigLIP routing, Groq-first/Gemini
fallback, FREE_ONLY, budgets and backoff. No retry is performed by queue generation.
If the head changes, re-export queues; stale snapshots cannot apply. Existing accepted
images, releases, human curation, historical registries and City Lab are untouched.
The mechanism uses task/identity/evidence state and applies to every city.
