# Jaipur safe-resolution apply — 4 October 2026

Published head: `india/rajasthan/jaipur/v3-research-jaipur-manual-01`.
Three approved decisions applied; 681 other records are byte-for-byte equivalent as JSON objects. No media was assigned, accepted, removed or newly verified. Numeric relevance and prominence scores were preserved.

## Applied Resolutions

The exact before/after field diff, including all description text, is in [safe_apply.diff.md](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-safe-resolution-01/apply/safe_apply.diff.md).

| Record | Exact fields changed | Result |
|---|---|---|
| Suraj Pol Gate | `alternate_names`, `description` | Existing `Surajpol Gate` retained; added `Surajpole Gate`, `Suraj Pol (Old Jaipur City)`. Description identifies the eastern walled-city gateway toward Galta and the Sun Temple. |
| India Gate | `name`, `name_en`, `alternate_names`, `description`, `tier` | Both names become `India Gate (Sitapura)`; alias becomes `["India gate"]`; description identifies the local Sitapura/Tonk Road landmark; tier becomes `recommended`. |
| Rooftop view stairs | `name`, `name_en`, `description`, `external_ids.osm_id`, `tier` | Both names become `Rooftop viewpoint access stairs (Chandpol Bazaar)`; reviewed access description added; canonical OSM reference changes from `node/12367918008` to `node/11533709370`; tier becomes `discovery`. |

Suraj Pol's place ID, coordinates, OSM `way/863303428` and Wikidata `Q140770830` are preserved. All coordinates are preserved. The old rooftop viewpoint OSM reference and all previous values remain in cumulative provenance, alongside the reviewed correction and related source evidence. Free-text classification recommendations were not converted into invented category/subcategory values.

## Deferred Resolutions

- Jain Mandir: listing/pin conflict remains unresolved; no Padampura rename, relocation, policy change or Sanghiji media. Queue flags include `IDENTITY_REVIEW` and `PIN_REVIEW_REQUIRED`.
- Haveli: exact building/visitor identity unresolved; no Samode mapping or imported media. Retains `IDENTITY_REVIEW` and policy review.
- Elephant Riding: exact operator/venue unresolved; no mapping to Elefantastic, Elephant Village, Amber rides or EleJungle, and no generic media. Retains `IDENTITY_REVIEW` and policy review.

All three complete published records and their existing assurance are unchanged.

## Media Policy Changes

Media policy is derived from tier using the existing deterministic policy function.

| Record | Before | After |
|---|---|---|
| Suraj Pol | REAL_REQUIRED | REAL_REQUIRED |
| India Gate | REAL_REQUIRED | REAL_PREFERRED |
| Rooftop stairs | REAL_REQUIRED | FALLBACK_ALLOWED |

India Gate's existing image remains explicitly unverified. No Patrika Gate, Amber Fort Suraj Pol or Panna Meena imagery was attached. Neither downgraded record appears in the required-image queues.

## Jaipur Before vs After

| Metric | Before | After |
|---|---:|---:|
| Published POIs | 684 | 684 |
| Total REAL_REQUIRED | 52 | 50 |
| Verified REAL_REQUIRED | 17 | 17 |
| REAL_REQUIRED coverage | 32.69% | 34.00% |
| Remaining required images | 35 | 33 |
| Critical blocker POIs | 661 | 660 |
| General usability | 3.36% (23 POIs) | 3.51% (24 POIs) |
| Source readiness | false | false |
| Source coverage validation | WARN | WARN |

The new pack remains `DRAFT_OFFLINE_PACK`; source certification is not ready. Coverage changed because two reviewed records legitimately changed policy, with zero newly verified photographs.

## New Resolution Queues

Final regenerated queue: [status_report.json](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-safe-resolution-01/resolution_queues-02/status_report.json).

- PROVIDER_RETRY: 16
- NEW_RESEARCH_REQUIRED: 14, including Old Jaipur City Suraj Pol
- MANUAL_REVIEW: 3 — Jain Mandir, Haveli, Elephant Riding

The first queue export is retained as an audit artifact. The final queue supersedes it after fixing the stale duplicate-candidate routing for a reviewed identity. A new research route requires a fresh alternative image and does not grant media acceptance or waive any importer/assurance hold.

## Suraj Pol Research Handoff

Registered handoff: `handoff_321f74590b9e8adf572da828`, from the new published source snapshot.

- [research_handoff.json](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-safe-resolution-01/suraj_pol_research/research_handoff.json)
- [research_handoff.md](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-safe-resolution-01/suraj_pol_research/research_handoff.md)
- [research_results.template.json](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-safe-resolution-01/suraj_pol_research/research_results.template.json)
- [research_results.schema.json](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-safe-resolution-01/suraj_pol_research/research_results.schema.json)

The task specifies a real reusable photograph of the eastern gate of Jaipur's historic walled city at `26.919156, 75.844935`, includes aliases, exact OSM/Wikidata anchors and municipal/government identity evidence, and excludes Amer/Amber Fort Suraj Pol and `Amber_Fort_-_Suraj_pol.jpg` with its source page.

## New Pack

`C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\rajasthan\jaipur\v3-research-jaipur-manual-01`

[Manifest](C:/Users/girir/Documents/YatraCanvas-DataFactory/releases/india/rajasthan/jaipur/v3-research-jaipur-manual-01/manifest.json)

The research-head registry points to this immutable pack. Applied changes and evidence are checksummed in `ai_repair.json` and appended to `field_provenance.json`.

## Tests

Final full-suite command, run with `PYTHONUTF8=1`:

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=reports/research/jaipur-safe-resolution-01/pytest-verified *> reports/research/jaipur-safe-resolution-01/pytest-verified.log
```

**379 passed in 46.15 seconds.** [Actual log](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-safe-resolution-01/pytest-verified.log).

The initial focused run passed 46 tests. Added regression coverage includes deferred record equality, stale snapshots/records, explicit unique approvals, human field locks, protected fields, deterministic 52-to-50 policy calculation, immutable publication, fresh registered snapshots, reviewed-identity duplicate routing and explicit pin review. Existing entity-substitution regressions cover Suraj/Amber, India/Patrika and rooftop/Panna Meena separation.

Reproduction and audit commands:

```powershell
.venv/Scripts/python.exe -m scripts.apply_jaipur_safe_resolution baseline
.venv/Scripts/python.exe -m scripts.apply_jaipur_safe_resolution supplement-baseline
.venv/Scripts/python.exe -m scripts.apply_jaipur_safe_resolution dry-run
.venv/Scripts/python.exe -m scripts.apply_jaipur_safe_resolution apply
.venv/Scripts/python.exe -m scripts.apply_jaipur_safe_resolution queues
.venv/Scripts/python.exe -m scripts.apply_jaipur_safe_resolution verify-supplement
.venv/Scripts/python.exe -m scripts.apply_jaipur_safe_resolution verify
```

Baseline capture is intentionally non-overwriting. A repeated apply against the old source fails the latest-head precondition. Host permissions were used only to hash the previously unreadable historical/runtime files; the remaining inventory was compared in the sandbox context.

## Safety and Validation

[validation_and_safety.json](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/research/jaipur-safe-resolution-01/validation_and_safety.json)

- Full JSON, JSONL, Parquet, SQLite integrity, referenced media and checksums validation passed. Reviewed fields also match the SQLite/Parquet exports.
- Pipeline health PASS; semantic data quality PASS; source coverage WARN. No claim of source readiness.
- All historical releases unchanged; all checksummed media and all 17 previously verified images preserved.
- All 681 unselected records unchanged; cumulative provenance history retained.
- Protected inventory: 42,337 files audited; zero unintended changes. City Lab: 9,983 files checked and unchanged.
- Human curation preserved; media importer unchanged; media assurance implementation and the complete published media-assurance sidecar unchanged.
- Paid AI calls = 0; provider calls = 0. The apply, queue and audit workflows are offline and instantiate no AI router.
- Intended implementation changes: new selective apply module and reproducible script/tests; exporter tier statistics are recalculated; queue routing/flags reflect the reviewed identity decisions. No historical pack, City Lab or curation file was edited.
