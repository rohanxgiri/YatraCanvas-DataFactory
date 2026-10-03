# YatraCanvas-DataFactory

Local intelligence and Research Handoff extend the existing free-only assurance
pipeline. See [the workflow](docs/local-research-workflow.md) for SigLIP, local
duplicate/text/geometry/hours validation, public research exports and safe imports.

```powershell
python -m datafactory.cli research-export --city Jaipur --all
python -m datafactory.cli research-import --file research_results.json --dry-run
python -m datafactory.cli research-import --file research_results.json --apply
```

Apply publishes a complete new offline pack; original v3 packs and City Lab remain
untouched. See [the architecture audit](docs/local-research-architecture.md) and
[four-city acceptance](reports/local_research_acceptance.md).

An autonomous, multi-source open-data extraction, deduplication, enrichment, and validation pipeline for generating offline-ready, structured city travel datasets (City Packs).

Given an input city such as `Jaipur, Rajasthan, India`, DataFactory automatically:
1. Resolves administrative boundaries and coordinates (Nominatim / GeoNames).
2. Extracts candidate places from Overture Maps Places GeoParquet and OpenStreetMap.
3. Filters non-travel places (ATMs, coaching classes, corporate offices, warehouses, utilities, parking lots).
4. Categorizes destinations into the canonical YatraCanvas taxonomy (heritage, museum, religious, park, nature, viewpoint, food, cafe, shopping, hotel, transport).
5. Deduplicates cross-provider entries using spatial grid indexing, coordinate proximity, and fuzzy string matching.
6. Enriches high-priority attractions with Wikidata entities, Wikipedia articles, and structured metadata.
7. Retrieves verified Wikimedia Commons imagery with strict license checks (CC / Public Domain) and converts to WebP formats (`primary.webp`, `thumbnail.webp`).
8. Reconciles durable CityPack Lab additions, exact-ID overrides, exclusions, and attributed media from `data/curated/<city_id>/`; malformed, conflicting, or orphaned work stops the build.
9. Computes quality confidence scores and planning heuristics (recommended visit duration, tourism priority), then restores authoritative human fields.
10. Quarantines low-quality, ambiguous, or out-of-boundary records.
11. Validates dataset integrity and exports JSON, JSONL, Parquet, SQLite (`yatracanvas.db`), checksums, and an interactive HTML quality report.

---

## Zero-Hallucination Policy

DataFactory adheres to a strict zero-hallucination principle:
- Important destinations require licensed real photography with source identity evidence and visual assurance. Missing or uncertain required photos remain unresolved.
- Missing opening hours or websites are stored as `null` or marked unverified.
- Less prominent places may use explicitly tagged category illustrations from licensed local pools. Fallback artwork never satisfies `REAL_REQUIRED` and never claims to depict a real destination.

---

## Installation

Requires Python 3.12+.

```bash
# Clone the repository
cd YatraCanvas-DataFactory

# Install dependencies and package in editable mode
pip install -e .
```

---

## Usage

### 1. Build a City Dataset

You can build a city dataset with a single command:

```bash
# Using build_city.py convenience script
python build_city.py "Jaipur, Rajasthan, India"

# Or using the datafactory module
python -m datafactory build --city "Jaipur" --state "Rajasthan" --country "India"
```

To build any other city (e.g. Udaipur, Varanasi, Mumbai):
```bash
python build_city.py "Udaipur, Rajasthan, India"
python -m datafactory build --city "Varanasi" --state "Uttar Pradesh" --country "India"
```

### 2. Resuming & Refreshing

To resume a build using cached raw downloads:
```bash
python -m datafactory build --city "Jaipur" --state "Rajasthan" --country "India" --resume
```

To force re-download of verified media:
```bash
python -m datafactory build --city "Jaipur" --state "Rajasthan" --country "India" --refresh-images
```

### 3. Validate a Release Package

To test schema conformance, SHA-256 checksums, SQLite database integrity, and local media existence:
```bash
python -m datafactory validate releases/india/rajasthan/jaipur/v1
```

### 4. Re-export SQLite

To re-export the SQLite deployment database (`yatracanvas.db`) from curated JSON records:
```bash
python -m datafactory export-sqlite Jaipur
```

---

## Pipeline Architecture & Directory Structure

```text
YatraCanvas-DataFactory/
├── data/
│   ├── raw/                  # Immutable downloaded source extracts
│   │   └── india/rajasthan/jaipur/
│   │       ├── overture/places_raw.parquet
│   │       ├── osm/places_raw.json
│   │       └── city_resolved.json
│   ├── cache/                # Disk cache for HTTP and API responses
│   ├── curated/              # Durable CityPack Lab curation and referenced media by city ID
│   ├── staging/              # Rejections, duplicates, quarantine, and curation reconciliation
│   └── media/                # Processed WebP images
│
├── releases/                 # Final versioned City Packs
│   └── india/rajasthan/jaipur/v1/
│       ├── city.json             # City metadata and boundary coordinates
│       ├── places.json           # Complete canonical places array
│       ├── places.jsonl          # Streaming newline-delimited JSON
│       ├── places.parquet        # Compact columnar Parquet dataset
│       ├── images_manifest.json  # Complete image attribution and license metadata
│       ├── sources.json          # Provider license declarations
│       ├── manifest.json         # Build statistics, record counts, and versions
│       ├── checksums.json        # SHA-256 digests for all release files
│       ├── yatracanvas.db        # Production SQLite database with spatial indexes
│       └── images/               # Processed WebP imagery (<place_id>/primary.webp, thumbnail.webp)
│
├── reports/                  # Quality audit reports
│   └── jaipur/latest/
│       ├── report.html           # Interactive visual inspection dashboard
│       └── summary.json          # Machine-readable QA metrics
│
├── config/                   # Configuration files
│   ├── categories.yaml           # YatraCanvas taxonomy & travel relevance rejection rules
│   ├── quality.yaml              # Scoring weights and quarantine thresholds
│   ├── planning_defaults.yaml    # Visit duration heuristics and interest tags
│   └── sources.yaml              # Source endpoints, rate limits, and timeouts
│
└── tests/                    # Automated pytest test suite
```

---

## Data Sources & Licensing

| Source | Role | License |
| :--- | :--- | :--- |
| **Overture Maps** | Primary large-scale candidate POIs | CDLA Permissive 2.0 |
| **OpenStreetMap** | Enrichment, tags, opening hours | Open Database License (ODbL) 1.0 |
| **Wikidata** | Entity resolution & structured facts | CC0 1.0 Universal Public Domain |
| **Wikimedia Commons** | Verified destination photography | Creative Commons (CC BY, CC BY-SA, CC0, Public Domain) |
| **Nominatim / GeoNames** | Administrative boundary & coordinate resolution | ODbL / CC BY 4.0 |

---

## Running Tests

Run the complete test suite with `pytest`:
```bash
pytest -v
```
Tests cover schema validation, coordinate geometry, taxonomy mapping, rejection filters, spatial deduplication, durable curation precedence, quarantine logic, SQLite queries, and manifest checksums.

## Free-only offline assurance

Copy `.env.example` to `.env` and enter `GROQ_API_KEY` and `GEMINI_API_KEY`. The local file is ignored by Git; keys are never printed. Process environment variables override `.env`. Confirm `GROQ_FREE_TIER_CONFIRMED=true` and `GEMINI_FREE_TIER_CONFIRMED=true` only for free accounts with paid billing disabled. `AI_MODE=FREE_ONLY` permits only the approved model list in `config/ai.yaml`. No paid provider, search, grounding or image-generation API is enabled. Source extraction works without either key.

```powershell
.\.venv\Scripts\python.exe -m datafactory ai-status
.\.venv\Scripts\python.exe -m datafactory ai-smoke --city Jaipur --state Rajasthan --place-id yc_in_rj_jaipur_kesar_kyari
.\.venv\Scripts\python.exe -m datafactory repair --city Jaipur --state Rajasthan --dry-run
.\.venv\Scripts\python.exe -m datafactory repair --city Jaipur --state Rajasthan --apply --network
.\.venv\Scripts\python.exe -m datafactory build-offline --city Manali --state "Himachal Pradesh" --from-release --network
```

`repair` defaults to a release-read-only audit using cached sources. It may populate decision caches and reports. `--network` permits bounded approved-source retrieval. Apply shares one AI budget with its preceding audit, bundles relative WebP paths and thumbnails, validates JSON/JSONL/Parquet/SQLite consistency and checksums, and publishes a separate immutable snapshot. Repeated output names receive a unique suffix; the console and report give the actual path. Published ID collisions stop apply for a reviewed migration. Verified human overrides and media remain authoritative. Fresh `build-offline` runs the existing source pipeline before repair; `--from-release` audits a snapshot without fresh discovery.

Reports live under `reports/<country>/<state>/<city>/assurance/`. The same sidecars are bundled with draft packs: `media_assurance.json`, `field_provenance.json`, `ai_repair.json`, and `usability.json`. Schema version 3.0 and existing SQLite columns remain compatible. Image metadata adds `image_type`, fallback identity, and content hash.

`DRAFT_OFFLINE_READY` means a structurally valid bundle suitable for review with unresolved issues recorded. `SOURCE_DATA_READY` additionally requires at least 95% usable published POIs and no critical blockers. Required real photos, identity, coordinate conflicts, travel-region association, attribution and local media are checked explicitly. Hours, descriptions and addresses measure coverage but are not fabricated to improve usability.

Default budgets: 30 inference requests, 20 vision requests, 5 escalations per city/build; source research and network media discovery each cover at most 20 places. Unchanged decisions reuse caches keyed by city, full identity, evidence, image bytes, prompt/schema, provider and model. Quota, timeout and unavailable jobs are saved for later retry; no long quota waits.

Fallback presentation belongs to the YatraCanvas app. `fallbacks.strategy: app` is the default: missing photos stay `images.primary: null`, so the app uses its existing local fallback images. Factory-generated artwork is removed from new exports of earlier repaired packs; authentic photos and verified human media choices are preserved. No app artwork is copied into a pack or labelled as destination photography. Pack renderability/usability remains a strict measure of bundled media; app fallback display is not counted as verified source media. The earlier artwork pools remain available only through an explicit `fallbacks.strategy: bundled` opt-in; authoring is never automatic.

`audit-identity --city ... --state ... --review-manifest <path>` reads a review queue locally and records collisions, pairwise evidence and proposed new candidate IDs. `--ai` explicitly enables transfer of reduced names, aliases, coordinates, categories and source identifiers to the configured providers; curator notes stay local. It never applies a published-ID migration or writes City Lab files. Missing/unsafe optional gallery references are pruned from new exports with an audit trail; primary-photo blockers remain explicit.

See `docs/architecture-audit.md` and the generated `reports/offline_assurance_acceptance.md` for acceptance evidence and limitations. `reports/app_fallback_transition.md` records the later removal of generated artwork from all four exports and gives the current pack paths. The original acceptance figures remain historical evidence.
