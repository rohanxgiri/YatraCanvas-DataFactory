# Local intelligence and research handoff

DataFactory uses deterministic/local evidence before the existing free-only Groq
then Gemini router. Missing external evidence becomes a research task immediately:
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
or `LOCAL_TEXT_ALLOW_DOWNLOAD=true`. Later runs use the normal Hugging Face cache.
Defaults are cache-only; restore flags to false after preparation. `HF_HOME` chooses
the cache directory. Pin `LOCAL_MEDIA_REVISION` to a model commit for reproducibility.
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
ML stack was not installed in this acceptance pass. This avoids large model/runtime
downloads in contributor setup and CI. No FAISS, vector database or new service.

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
python -m datafactory.cli research-export --city Jaipur --state Rajasthan --country India --all
python -m datafactory.cli research-export --city Jaipur --type OPENING_HOURS
python -m datafactory.cli research-export --city Jaipur --priority P0,P1
python -m datafactory.cli research-export --cities Jaipur,Udaipur,Varanasi,Manali --all
```

Default source is the latest research-imported head, then `v3-app-fallbacks`, then
`v3`. `--version` chooses an explicit snapshot. Same-name cities require state/country
disambiguation. `--all` includes all unresolved task types for important POIs.
Ordinary commercial POIs are excluded unless `--include-optional` is explicit.
Important means core destinations, destinations requiring/preferring real imagery,
and recommended travel experiences; recommended cafes with ordinary fallback
policy do not create hours/website/description tasks by default.
Prominent required-image cafes/food destinations still get P0 tasks. Descriptions
are restricted to core and important recommended attractions/experiences.

Outputs under `data/research/exports/<country>/<state>/<city>/`:

- `research_handoff.json`: canonical tasks, stable IDs, explicit city/place context,
  reduced public evidence and explainable priority.
- `research_handoff.md`: ChatGPT-ready instructions and task context.
- `research_handoff.csv`: optional spreadsheet review; not an import format.
- `research_results.schema.json`: strict typed payloads, no researcher confidence.
- `research_results.template.json`: UNRESOLVED entries ready to fill.

Types: OPENING_HOURS, REAL_PRIMARY_IMAGE, WEBSITE, DESCRIPTION, COORDINATE_RESEARCH,
IDENTITY_RESEARCH. Future types extend the enum/schema/selector/validator, leaving
the interchange intact. Priority: P0 required photographs; P1 identity/coordinates;
P2 important hours; P3 preferred photographs; P4 optional metadata.

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
python -m scripts.report_local_research
python -m pytest -q -p no:cacheprovider --basetemp=scratch/local-research-verification
```

The report measures cached local/model/cloud counts, without monetary claims or
invented savings. Optional real model integration is separate from default tests.
