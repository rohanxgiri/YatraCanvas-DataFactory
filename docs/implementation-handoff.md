# Offline assurance handoff

Updated 3 October 2026. Continue from actual artifacts rather than reconstructing
counts from older exports.

The latest implementation passes 151 offline tests. Dataset acceptance is not.
The user rejected the generated fallback artwork. Default fallback strategy is now
`app`; missing photos stay null so the YatraCanvas app selects its existing assets.
Read `reports/app_fallback_transition.md` first for current output paths and strict
pack-media metrics. The four current deliverables are the `v3-app-fallbacks`
directories under each city's release directory. The original 16-section report and
`reports/offline_final_verification.json` describe the earlier snapshots. Earlier
snapshots and failed temporary exports were preserved; some older Windows private
ACL directories are inaccessible from the sandbox. New exports inherit parent ACLs.

Use `.venv/Scripts/python.exe`. The test command is recorded in the final report.
The report can be reproduced with:

```powershell
.\.venv\Scripts\python.exe scripts/report_offline_acceptance.py
```

The source City Lab manifests are:

- `C:/Users/girir/Documents/YatraCanvas-CityPack-Lab/assets/city_packs/jaipur/review_candidates.json`
- `C:/Users/girir/Documents/YatraCanvas-CityPack-Lab/assets/city_packs/udaipur/review_candidates.json`
- `C:/Users/girir/Documents/YatraCanvas-CityPack-Lab/assets/city_packs/varanasi/review_candidates.json`

They contain 13, 3 and 3 canonical-ID conflict groups respectively. Local audit
reports are under each DataFactory city's `reports/india/.../assurance/identity_review.json`.
All groups remain in review. Do not edit City Lab, merge groups or migrate published
IDs without authorization. Automatic approval review rejected sending its candidate
payload externally. A reduced-field transfer question remains pending; local-only
`audit-identity` is the default, while `--ai` explicitly enables inference.

Both accounts were explicitly confirmed free with paid billing disabled. Credentials
are private in `.env`; never reproduce them. AI budgets and source discovery bounds
are intentional. Current exports retain zero paid feature/provider usage. Quota and
service failures are reported as unresolved. Do not silently raise budgets or
certify missing required media to reach the usability target.

Next work is authoritative source research and licensed photo verification for
remaining required-media blockers, followed by another bounded repair pass when
free quota is available. Resolve the absent/policy-mismatched 18-case IDs explicitly.
Keep factual corroboration independent of model opinions. Existing user changes,
original v3 sources and human curation must be preserved.


## Bundled city-data loop — 2026-10-04

`[IMPLEMENTED]` See [the city-data loop](CITY_DATA_DEV_LOOP.md) for the new immutable app export, base-bound human repair patch and safe sync commands. Existing strict certification/provider architecture remains intact. `[PARTIAL]` Physical-phone acceptance remains unverified. No production migration or paid provider call is part of this loop.
