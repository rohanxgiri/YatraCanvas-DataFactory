"""Render the measured recovery results into the requested report format."""
import json
from pathlib import Path

here=Path(__file__).resolve().parent
s=json.loads((here/'summary.json').read_text(encoding='utf-8'))
root=here.parents[2]
versions=[s['before_research'],s['images01'],s['images02_final']]
table=['Metric | Before research | images-01 | images-02 final','--- | ---: | ---: | ---:']
for label,key in [('General usability','GENERAL_USABILITY'),('REAL_REQUIRED coverage','REAL_REQUIRED_MEDIA_COVERAGE'),('Verified required images','real_required_verified'),('POIs with critical blockers','critical_blocker_pois'),('Missing renderable media','MEDIA_NOT_RENDERABLE'),('Unresolved required media','CORE_MEDIA_UNRESOLVED'),('Source readiness','SOURCE_DATA_READY')]:
    values=[v['critical_blockers'][key] if key in {'MEDIA_NOT_RENDERABLE','CORE_MEDIA_UNRESOLVED'} else v[key] for v in versions]
    if key in {'GENERAL_USABILITY','REAL_REQUIRED_MEDIA_COVERAGE'}: values=[str(v)+'%' for v in values]
    if key=='real_required_verified':values=[str(v)+'/52' for v in values]
    if key=='SOURCE_DATA_READY':values=['Ready' if v else 'Not ready' for v in values]
    table.append(label+' | '+' | '.join(map(str,values)))
changed=['config/sources.yaml','datafactory/ai/providers.py','datafactory/ai/router.py','datafactory/cli.py','datafactory/models/media_candidate.py','datafactory/pipeline/media_assurance.py','datafactory/pipeline/image_content.py','datafactory/research/importer.py','datafactory/research/media_evidence.py','datafactory/research/retry.py','datafactory/sources/wikimedia.py','datafactory/utils/media_metadata.py','docs/local-research-workflow.md','tests/test_research_handoff.py','tests/test_research_media_recovery.py']
files='\n'.join('- `'+p+'`' for p in changed)
accepted='; '.join(s['accepted_names'])
reused='; '.join(s['reused_asset_names'])
p18='; '.join(s['p18_names'])
text=f'''# Jaipur Research Media Importer Recovery

13 additional results accepted. Final immutable output: `{s['output_pack']}`.

## Root Causes

- **DUPLICATE_IMAGE:** the old importer seeded a per-POI duplicate index with its existing primary/gallery, then reviewed every match before resolving same-asset reuse or new identity evidence.
- **MPO:** deterministic format validation rejected Pillow-confirmed MPO before extracting a bounded primary frame. Four prior MIME rejects were visible; a fifth MPO was previously hidden behind Lake Palace's license mismatch.
- **LICENSE CONFLICT:** raw legal URL/name and creator equality treated trailing slashes, known CC HTTP/HTTPS variants and NFC-equivalent names as conflicts. Commons filename parsing had also lost semicolon suffixes.
- **OVERSIZED COMMONS FILE:** a 24,469,664-byte original exceeded the unchanged 20,000,000-byte budget; the old path had no derivative fallback. During recovery, Commons returned a valid derivative on `thumb.wikimedia.org`; the initial derivative allowlist recognized only `upload.wikimedia.org`. That precise omission was corrected, with the same Commons path, API file identity, byte and decoded-dimension checks.
- **CLOUD ASSURANCE HOLD:** generic `research_import` candidates lost actual P18/known-method evidence, so identity-resolved media still routed to cloud. Genuine identity/composition uncertainty and free-provider availability also caused holds. Earlier diagnostics dropped exact HTTP causes.

## Changes Made

Pure legal/file normalization lives in `utils`, source/asset evidence merging in `research/media_evidence.py`, bounded primary-frame normalization in `pipeline/image_content.py`, and registered retry mapping in `research/retry.py`. Existing importer, assurance, router, exporters and schemas remain the workflow. SigLIP alone cannot accept; safety thresholds and FREE_ONLY gates remain unchanged.

Changed code, configuration, documentation and tests:

{files}

## Existing Asset Reuse

19 results matched eligible same-POI assets; **10 were accepted and reused byte-for-byte**, while 9 still required assurance. All 10 original Commons filenames independently agree with the researched file. Cross-POI exact duplicates, unrelated near duplicates, verified metadata conflicts, changed identity and contradictory QIDs remain blocked by regression tests. No duplicate holds remain in this real retry.

Reused: {reused}.

## P18 Evidence Recovery

**9 accepted deterministically** through actual POI QID → Wikidata P18 → exact verified Commons file, with `wikidata_p18`, related entity ID, .99 source confidence and verified original license. Other exact source methods were retained for 14 evaluated results. Existing Wikidata source-cache conventions are retained; no filename inference establishes P18.

P18: {p18}.

## MPO Recovery

Encountered **5**, normalized **5**, accepted **1** (Dalaram Bagh), rejected **0** by MPO/content mechanics, held **4** for unchanged assurance requirements. Only the primary frame is used. Byte, pixel, geometry and decode limits still apply.

## License Normalization

Known license/name/URL formatting canonicalized for **34** FOUND results; **2** NFC creator normalizations. Lake Palace's CC0 conflict is resolved; its normalized photograph remains held for identity assurance/provider availability. No license holds remain. Original research input remains byte-identical with SHA-256 `126c3f0dad105e87b2079f04bd244089ab9b77f27f53ae6b933e258365c32ec9`.

## Commons Derivatives

**1 oversized original recovered:** Govind Devji Temple. Commons API supplied a **1920 × 1277**, **697,956-byte** derivative. The original Commons page, filename, creator and CC BY-SA 4.0 provenance remain stored. The derivative verified the same local asset, which was reused. No AI calls were needed. Only exact official thumbnail hosts are allowed, with redirects blocked and the 20 MB ceiling unchanged.

## Cloud Routing

- Deterministically accepted: **9**; accepted through cloud: **4**.
- SigLIP assessed: **25**, comprising **13 fresh inferences + 12 cached assessments**. No SigLIP-only acceptance.
- Groq calls: **10**; Gemini calls: **6**; paid calls: **0**.
- Provider availability held **16** results. Actual **Groq HTTP 429** and **Gemini HTTP 503** are retained in safe structured diagnostics. The existing router cooldowns/budgets were respected; this pass did not repeatedly retry those holds.

## Retry Bundle

Initial fresh handoff: `handoff_5bc527aa3426a26aa66609b7`, generated from images-01, **49** remaining tasks, Akshardham excluded. Classification: **34 RETRYABLE_WITH_EXISTING_RESEARCH**, **1 NEW_RESEARCH_REQUIRED** (PARTIAL), **6 GENUINE_CONFLICT**, **8 UNRESOLVED_NO_SOURCE**. Source URLs and research evidence were copied unchanged; task IDs came from the new registry and retain the project's stable ID convention.

Dry run: **49 supplied, 49 matched, 49 valid, 0 auto-applicable, 41 review, 0 rejected, 0 missing POIs, 0 invalid sources, 0 invalid schedules, 41 requiring media verification, 8 unresolved**. Reasons: 34 MEDIA_DOWNLOAD_OR_VERIFICATION_REQUIRED, 1 RESEARCH_PARTIAL, 6 RESEARCH_CONFLICT, 8 RESEARCH_UNRESOLVED. No structural failure.

After images-02 published, another fresh handoff (`handoff_e1c89154ae9bf304fd0e2ce8`) safely mapped all 37 remaining tasks. A schema-valid registered subset containing only Govind Devji avoided repeating unchanged assurance calls. Its dry run matched/validated 1, reviewed 1 for media retrieval, rejected 0; apply accepted 1 without AI.

A final fresh handoff for the **36** remaining required images is ready at `{s['remaining_handoff']['path']}` (`{s['remaining_handoff']['handoff_id']}`). Earlier retry handoffs are historical snapshots; future applies must respect the current research head.

## Apply Result

Initial images-02 apply: **12 applied / 26 review / 3 rejected / 8 unresolved**.
Supplementary derivative apply: **1 applied / 0 review / 0 rejected / 0 unresolved**.
Net result across the 49 remaining tasks: **13 applied / 25 review / 3 rejected / 8 unresolved**.

Downloaded successfully: **34/34 FOUND**. Accepted as real primary images: **13**. Deterministic content rejections: **0**. License holds: **0**. Provider holds: **16**. Assurance quality/identity holds or rejections: **5**. Research requiring new evidence: **15** (1 partial, 6 conflicts, 8 unresolved).

Accepted: {accepted}.

## Jaipur Readiness

{chr(10).join(table)}

The final column is the preserved images-02 recovery plus its derivative supplement. The intermediate images-02 measured 3.07% usability, 28.85% coverage and 15/52 verified images. Coordinate and travel-region blockers remain **2 each**. No source readiness target was claimed.

## Safety

- Original v3, all original/source packs and images-01 unchanged: **23,728 protected file hashes matched**.
- Intermediate images-02 preserved: **120 file hashes matched**.
- Human curation, FREE_ONLY configuration and `.env` unchanged (included in the protected manifest).
- City Lab unchanged: no City Lab paths, tools, imports or synchronization were used.
- Paid AI calls = **0**. No providers or large dependencies added. Registered IDs, snapshots, human locks, licensing and transaction protections remain active.

## Tests

Final full test command (from the repository, project virtual environment):

```powershell
$env:PYTHONUTF8='1'
.\\.venv\\Scripts\\python.exe -m pytest -q -p no:cacheprovider --basetemp data/staging/recovery-tests-final-02 --tb=short
```

**{s['tests']['passed']} passed in {s['tests']['seconds']:.2f}s**, recorded in `tests-final-02.txt`. Default tests use mocked HTTP and no real cloud/model calls. Focused recovery suite previously passed **136 tests**; the final suite adds cold CLI startup, official thumbnail host and verified metadata conflict regressions.

```powershell
.\\.venv\\Scripts\\python.exe -m datafactory.cli validate releases/india/rajasthan/jaipur/v3-research-jaipur-images-02
.\\.venv\\Scripts\\python.exe -m datafactory.cli validate releases/india/rajasthan/jaipur/v3-research-jaipur-images-02-derivative-01
.\\.venv\\Scripts\\python.exe reports/research/jaipur-media-recovery/verify_recovery.py
```

Both packs pass structural/semantic validation: JSON/JSONL/Parquet/SQLite projections, SQLite integrity, referenced images and checksums. Final pipeline health **PASS**, data quality **PASS**, source coverage **WARN**. Additional audit fully decoded **26 new WebP assets**, checked bound assurance hashes and research provenance for all 13 accepted POIs, and recalculated readiness against the published output.

Corrected verification issues: initial test fixtures omitted required `downloaded_at` fields; fixtures were corrected without relaxing the production model. CLI cold startup raised `ImportError: cannot import name 'WikimediaCommonsClient' from partially initialized module` because the new pure helper was placed behind the pipeline initializer; moving it to utils resolved the cycle and a cold-start regression covers it. The first custom audit raised `KeyError: 'task_id'` on legacy provenance rows; the auditor now searches research rows safely, without changing those rows. The actual Commons host failure and recovery are reported above.

## Remaining Work

**Importer/media mechanics:** the observed duplicate-reuse, P18, MPO, legal formatting, filename parsing and oversized-download mechanics are resolved. **16** files await free-provider recovery or stronger independent identity evidence; preserve their research rather than requesting it again. Do not bypass the router cooldowns or import stale handoffs.

**Image suitability:** Anokhi Museum, Jantar Mantar and Jawahar Circle were rejected by unchanged cloud assurance; Jhalana/Amagarh and Sawai Mansingh Townhall stayed in review. Better identity/composition evidence or alternative photographs may be needed; thresholds stay intact. See `held_images.json` for exact model reasons and unmet requirements.

**Genuinely missing/conflicting external research:** **1 partial**, **6 conflicts**, **8 unresolved** need further evidence. The fresh 36-task handoff reflects all remaining required media. Broader source readiness still requires 641 missing renderable media and the existing coordinate/region blockers to be addressed through their normal workflows.
'''
(here/'report.md').write_text(text,encoding='utf-8')
print(here/'report.md')
