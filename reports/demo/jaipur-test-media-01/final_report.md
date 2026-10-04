# Suraj Pol local/demo-only photograph

## Suraj Pol

| Field | Result |
|---|---|
| Identity | RESOLVED — Old Jaipur City Suraj Pol / Surajpole Gate |
| Place ID | `yc_in_rj_jaipur_suraj_pol_gate` |
| Coordinates | `26.919156, 75.844935` |
| OSM / Wikidata | `way/863303428` / `Q140770830` |
| Test image | `suraj_pol_old_jaipur_test.jpg`, manually supplied by the user |
| Source | [JaipurThruMyLens](https://jaipurthrumylens.com/2016/10/06/history-old-city-gates-of-jaipur-architectural-design-elements/) |
| Media class | `TEST_ONLY_REAL` |
| Demo renderable | YES — local thumbnail and place-detail photograph visually verified |
| Strict verified | UNRESOLVED |
| Strict license | UNVERIFIED, `license_verified=false` |
| Counts toward source readiness | false |

The supplied image visually matches the source page's Surajpol photograph. The metadata preserves the original filename, original-input SHA-256, import timestamp, source/reference URL, explicit human confirmation, municipal/OSM/Wikidata evidence and exclusions for Amber Fort Suraj Pol, Jorawar Singh Gate and Ajmeri Gate. Visible source marks remain intact.

## Files Created

New immutable release:

`C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\rajasthan\jaipur\v3-demo-jaipur-test-media-01`

Fully local, explicitly enabled demo projection:

`C:\Users\girir\Documents\YatraCanvas-DataFactory\releases\india\rajasthan\jaipur\v3-demo-jaipur-test-media-01\demo`

- [Test image — primary.webp](C:/Users/girir/Documents/YatraCanvas-DataFactory/releases/india/rajasthan/jaipur/v3-demo-jaipur-test-media-01/media/test_only/yc_in_rj_jaipur_suraj_pol_gate/a3dcf425fc22eeb8/primary.webp)
- [Thumbnail — thumbnail.webp](C:/Users/girir/Documents/YatraCanvas-DataFactory/releases/india/rajasthan/jaipur/v3-demo-jaipur-test-media-01/media/test_only/yc_in_rj_jaipur_suraj_pol_gate/a3dcf425fc22eeb8/thumbnail.webp)
- [Metadata — metadata.json](C:/Users/girir/Documents/YatraCanvas-DataFactory/releases/india/rajasthan/jaipur/v3-demo-jaipur-test-media-01/media/test_only/yc_in_rj_jaipur_suraj_pol_gate/a3dcf425fc22eeb8/metadata.json)
- [Test-media manifest](C:/Users/girir/Documents/YatraCanvas-DataFactory/releases/india/rajasthan/jaipur/v3-demo-jaipur-test-media-01/test_media_manifest.json)
- [Offline demo preview](C:/Users/girir/Documents/YatraCanvas-DataFactory/releases/india/rajasthan/jaipur/v3-demo-jaipur-test-media-01/demo/preview.html)
- [Human identity confirmation](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/demo/jaipur-test-media-01/manual_identity_confirmation.json)
- [Import receipt](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/demo/jaipur-test-media-01/import_receipt.json)

Primary output is WebP at the original 640×459 pixels; thumbnail is 400×287. Decode, EXIF orientation handling, bounded resize and re-encoding are covered by tests. No upscaling or production-license acceptance occurred.

## Generic Support and Defaults

`test-media-import` accepts any explicitly human-confirmed exact local photograph; it has no POI-specific identity heuristics. Confirmation binds file bytes to the current exact place identity. Altered bytes, stale pins/IDs and wrong gates fail closed.

```powershell
.venv/Scripts/python.exe -m datafactory test-media-import --image-file <local-image> --confirmation-file <confirmation.json> --source-pack <current-strict-pack> --output-version <new-version> --allow-test-media
```

`ALLOW_TEST_MEDIA=true` is the equivalent explicit CLI configuration. The default is false. The display selector defaults to strict mode; enabling test media never changes the production assurance sidecar.

Demo priority is `VERIFIED_REAL`, `TEST_ONLY_REAL`, approved `AI_FALLBACK`, then approved `GENERIC_FALLBACK`. Strict mode skips `TEST_ONLY_REAL`. Test records and future imports remain separate in `data/test_media/<city-key>/registry.json` and immutable packs.

The new release root retains strict source records and primary assignments. `demo/` contains separate JSON, JSONL, Parquet, SQLite, local assets, metadata and checksums, marked `production_release=false`. A demo pack consumer must use `demo/`. Strict consumers must use the root.

## Metrics

| Metric | Before | After |
|---|---:|---:|
| Strict REAL_REQUIRED total | 50 | 50 |
| Strict verified REAL_REQUIRED | 17 | 17 |
| Strict verified coverage | 34.00% | 34.00% |
| Strict source readiness | false | false |
| Demo required renderable coverage | — | 18/50 = 36.00% |
| Demo renderable coverage, all published POIs | — | 18/684 = 2.63% |
| Test-only renderable photographs | 0 | 1 |

The demo selector excludes unverified existing photos, so these demo metrics count the 17 verified photographs plus the one explicitly confirmed test photograph. They do not count all legacy files merely because they are on disk.

## Tests

Final full-suite command, with `PYTHONUTF8=1`:

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=reports/demo/jaipur-test-media-01/pytest-final *> reports/demo/jaipur-test-media-01/pytest-final.log
```

**396 passed in 48.05 seconds.** [Actual log](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/demo/jaipur-test-media-01/pytest-final.log).

Focused test-media suite: **17 passed**. Covers opt-in/default strict behavior, verified-first ordering, fallback ordering, wrong-gate identity rejection, input-byte binding, explicit manual confirmation, license isolation even with a spoofed verification boolean, decode/orientation/no-upscale normalization, immutable history and fully local demo export.

Actual build/audit commands:

```powershell
.venv/Scripts/python.exe -m scripts.suraj_test_media_demo baseline
.venv/Scripts/python.exe -m scripts.suraj_test_media_demo supplement-baseline
.venv/Scripts/python.exe -m scripts.suraj_test_media_demo build
.venv/Scripts/python.exe -m scripts.suraj_test_media_demo verify-supplement
.venv/Scripts/python.exe -m scripts.suraj_test_media_demo verify
```

Card and detail preview were inspected in the browser through a loopback-only local server. Both images decoded successfully using local relative paths; no internet image request is required. [Browser validation](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/demo/jaipur-test-media-01/browser_validation.json).

## Safety

[Validation and safety evidence](C:/Users/girir/Documents/YatraCanvas-DataFactory/reports/demo/jaipur-test-media-01/validation_and_safety.json).

- Strict assurance implementation and complete published assurance sidecar unchanged.
- Production media importer unchanged; strict verified count remains 17 and strict coverage remains 34.00%.
- All historical releases unchanged, including `v3-research-jaipur-manual-01`; all 17 accepted image assets preserved.
- Strict canonical JSON/JSONL, field provenance and usability are unchanged. Strict research-head registry remains at `v3-research-jaipur-manual-01`.
- City Lab and human curation unchanged. Protected inventory: 42,459 files checked, zero unintended changes.
- New root and demo projections pass JSON, JSONL, Parquet, SQLite, local-media and checksum validation. Source coverage remains WARN; source readiness remains false.
- Paid AI calls = 0; provider calls = 0.

## Application Boundary

This phase changes DataFactory and generates a complete offline demo pack/preview. The separate Flutter `YatraCanvas` repository currently uses a static image map and does not automatically consume this demo pack. It was inspected read-only and has not been changed. Direct Flutter wiring is a separate optional scope choice presented in chat; the successful rendering assertion here refers to the generated offline demo card/detail preview and local demo export, not a rebuilt native Flutter application.
