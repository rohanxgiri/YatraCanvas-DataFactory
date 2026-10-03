# Local intelligence and research handoff architecture

The prior phase already implements free-only Groq/Gemini routing, decision caching,
source evidence indexing, media licensing/downloading/WebP generation, identity
and regional coordinate assurance, human locks, fallback policies, usability,
and immutable transactional offline export. These remain the owners of their
existing responsibilities; City Lab and original v3 releases are outside this work.

New `local_intelligence` adapters run before cloud decisions: ImageHash fingerprints,
bounded optional SigLIP batches with persistent score caching, the existing
RapidFuzz normalizer plus optional sentence embeddings, Shapely polygon distances,
and mature OSM schedule parsers. Similarity is supporting evidence, never identity
proof. Verified Wikidata P18 evidence outranks similarity. Local models are lazy,
cache-only by default, and fail open to the existing assurance path.

New `research` schemas/export/import build stable city-scoped tasks from unresolved
pack assessments. Export writes public, reduced evidence and a ChatGPT-ready prompt.
Import matches registered task/place IDs and snapshot fingerprints, derives source
quality locally, respects human locks, validates hours and media through existing
assurance, and publishes a separate offline pack before committing import history.
Dry runs perform no writes or downloads. Identity migrations remain review-only.

Repair emits unresolved tasks without cloud calls for empty media discovery or
absent source hours. The existing exporter owns JSON/JSONL/Parquet/SQLite and media
projections. Research import immediately rebuilds a complete immutable snapshot;
the returned version is the source for subsequent repair/build-offline work.
