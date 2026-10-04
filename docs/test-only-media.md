# Local demo photographs

`TEST_ONLY_REAL` is a separate human-confirmed media record. It is not a production-media acceptance result. The strict source records, `media_assurance.json`, verified count and research head remain unchanged.

Import requires a local JPEG/PNG/WebP, an explicit manual confirmation, and `--allow-test-media` (or `ALLOW_TEST_MEDIA=true`). A confirmation binds the supplied file's SHA-256 to the exact place ID and complete current identity digest; names and filename similarity cannot establish identity. The confirmation schema is exported with each new demo-capable pack.

```powershell
.venv/Scripts/python.exe -m datafactory test-media-import --image-file <local-photo> --confirmation-file <manual-confirmation.json> --source-pack <current-strict-pack> --output-version <new-version> --allow-test-media
```

Human confirmation must include `identity_verified=true`, `real_photograph_confirmed=true`, `license_verified=false`, a public reference page, the original filename, reviewer context, and identity evidence. This workflow performs no image search or automatic acceptance of arbitrary online images.

The normalizer validates decode and dimensions, applies EXIF orientation, bounds the primary to 1280 pixels and the thumbnail to 400 pixels, and writes WebP without upscaling. It preserves visible source marks. Original filename, input SHA-256, source/reference page, import timestamp, identity evidence and unverified-license status remain in `metadata.json` and `test_media_manifest.json`.

The new immutable version has two projections:

- The root contains the ordinary **strict** JSON/JSONL/Parquet/SQLite exports and unchanged primary-media assignments. Test assets are isolated under `media/test_only/`; their manifest is disabled by default.
- `demo/` contains the explicitly enabled **local demo** JSON/JSONL/Parquet/SQLite exports, selected primary images, local image/thumbnail copies, metadata, checksums and an offline card/detail preview. This projection is marked `production_release=false` and `counts_toward_source_readiness=false`. Point a demo pack consumer at this directory. Use the root directory for strict consumers.

`select_display_media(..., allow_test_media=False)` is strict by default. Selection priority when enabled is verified real photograph, identity-bound test-only photograph, approved AI fallback, then approved generic fallback. Strict mode skips test-only photographs. Unverified existing photos do not become verified merely by being present on disk. The existing production importer and licensing/assurance implementation are unchanged.

Future imports retain valid previous test records through `data/test_media/<city-key>/registry.json`. Stale identity bindings fail closed. Repeated version names create separate immutable snapshots. Demo publication never updates the strict research head.

`demo_required_renderable_coverage` counts displayable selections among REAL_REQUIRED POIs. `demo_renderable_media_coverage` counts displayable selections among all published POIs. Both are display metrics, separate from strict verified coverage. Even if an assurance boolean is erroneously true, `image_type=test_only_real` and `license=UNVERIFIED_TEST_ONLY` cannot certify a test photograph through the existing strict usability calculation.
