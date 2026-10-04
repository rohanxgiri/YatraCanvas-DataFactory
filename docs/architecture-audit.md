# Architecture audit and implementation plan

The existing v3 pipeline resolves cities with GeoNames/OSM/Wikidata, extracts Overture,
OSM, Wikivoyage and Wikidata candidates, normalizes travel relevance, votes on taxonomy,
deduplicates in `CanonicalPlaceGraph`, enriches from Wikipedia/Wikidata, processes
Commons images, applies durable human curation, scores/quarantines, then exports
JSON/JSONL/Parquet/SQLite and manifests. `CityMetadata` is the shared city context.
HTTP response caches and source retry infrastructure already exist. There is no
AGENTS.md in this checkout or its inspected parent directories; docs/tools directories
did not exist. Existing working changes and release data belong to the user and are
preserved as the baseline.

Gaps: no AI provider/router/budget layer, no visual assurance, permissive substring
license matching, no Openverse adapter, no fallback pools, no transparent offline
usability gate. Existing Commons search can apply uncertain photos. Distinct same-name
entities receive identical canonical IDs. Global conflict reports append across cities.
Geographic quarantine treats municipal bbox exclusion as invalidity.

Implementation uses additive image fields and assurance/provenance sidecars, preserving
schema version 3.0 and mobile SQLite columns. AI validates supplied evidence; it never
becomes a factual source. REAL_REQUIRED needs a verified actual photo with identity,
quality, local assets and legal provenance. Usability counts published records without
hiding unresolved blockers. Draft readiness and source readiness are distinct.

Order: free-only configuration, provider adapters, strict decisions/router/cache/budgets,
normalized media/Openverse, media assurance and stable fallback pools, identity/region/
coordinate audits, grounded metadata extraction, repair dry-run/apply, usability,
build-offline orchestration, cached real-city benchmarks, offline tests/documentation.
Live account model checks precede inference, and a single smoke job precedes batching.
Missing credentials or unconfirmed free-account billing defer inference safely.

Later user correction: fallback presentation belongs to the existing YatraCanvas
app. Factory artwork is disabled by default through `fallbacks.strategy: app`.
Absent photos remain null; app assets are neither copied nor declared factual media.
New snapshots retire only factory-authored artwork and preserve authentic photos and
verified human media. Strict bundle usability continues to require actual bundled
media, so its earlier artwork-based percentages are historical rather than a claim
about app rendering. See `reports/app_fallback_transition.md` for current exports.


## Bundled city-data loop — 2026-10-04

`[IMPLEMENTED]` See [the city-data loop](CITY_DATA_DEV_LOOP.md) for the new immutable app export, base-bound human repair patch and safe sync commands. Existing strict certification/provider architecture remains intact. `[PARTIAL]` Physical-phone acceptance remains unverified. No production migration or paid provider call is part of this loop.
