# YatraCanvas-DataFactory

An autonomous, multi-source open-data extraction, deduplication, enrichment, and validation pipeline for generating offline-ready, structured city travel datasets (City Packs).

Given an input city such as `Jaipur, Rajasthan, India`, DataFactory automatically:
1. Resolves administrative boundaries and coordinates (Nominatim / GeoNames).
2. Extracts candidate places from Overture Maps Places GeoParquet and OpenStreetMap.
3. Filters non-travel places (ATMs, coaching classes, corporate offices, warehouses, utilities, parking lots).
4. Categorizes destinations into the canonical YatraCanvas taxonomy (heritage, museum, religious, park, nature, viewpoint, food, cafe, shopping, hotel, transport).
5. Deduplicates cross-provider entries using spatial grid indexing, coordinate proximity, and fuzzy string matching.
6. Enriches high-priority attractions with Wikidata entities, Wikipedia articles, and structured metadata.
7. Retrieves verified Wikimedia Commons imagery with strict license checks (CC / Public Domain) and converts to WebP formats (`primary.webp`, `thumbnail.webp`).
8. Computes quality confidence scores and planning heuristics (recommended visit duration, tourism priority).
9. Quarantines low-quality, ambiguous, or out-of-boundary records.
10. Validates dataset integrity and exports JSON, JSONL, Parquet, SQLite (`yatracanvas.db`), checksums, and an interactive HTML quality report.

---

## Zero-Hallucination Policy

DataFactory adheres to a strict zero-hallucination principle:
- If a place does not have a verified Wikidata P18 image or confirmed Commons category match, its primary image is recorded as `null`.
- Missing opening hours or websites are stored as `null` or marked unverified.
- Generic category fallback images (e.g. assigning a generic mountain photo to a missing museum) are strictly prohibited.

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
│   ├── staging/              # Staging logs: rejected_places.jsonl, duplicates.jsonl, quarantine/
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
Tests cover schema validation, coordinate geometry, taxonomy mapping, rejection filters, spatial deduplication, quarantine logic, SQLite queries, and manifest checksums.
