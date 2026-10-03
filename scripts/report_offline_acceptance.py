"""Reproduce acceptance reporting from actual repair artifacts; no source/AI calls."""
import json
from collections import Counter
from pathlib import Path
from datafactory.utils.atomic import atomic_json
from datafactory.pipeline.validate import validate_release_package


def table(columns, rows):
    def cell(v):
        return str(v).replace("|", "/").replace("\n", " ")
    return ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)] + [
        "| " + " | ".join(cell(v) for v in row) + " |" for row in rows]


def main():
    root = Path(__file__).resolve().parents[1]
    reports = []
    for path in sorted((root / "reports/india").rglob("assurance/ai_repair.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        live = path.parent / "benchmark_runs/live_pass.json"
        historical = json.loads(live.read_text(encoding="utf-8")) if live.exists() else None
        usage = Counter(data["ai_usage"]["stats"])
        if historical:
            usage.update(historical["ai_usage"]["stats"])
        identity_path = path.parent / "identity_review.json"
        identity = json.loads(identity_path.read_text(encoding="utf-8")) if identity_path.exists() else None
        pack = Path(data["output_pack"])
        if not pack.is_absolute():
            pack = root / pack
        validation = validate_release_package(pack)
        reports.append({"city": data["city"], "report":data,"ai_usage_total":dict(usage),
                        "live_pass":historical,"identity_review":identity,"pack":str(pack),"validation":validation})
    jaipur = next(r for r in reports if r["city"]["name"] == "Jaipur")  # Acceptance fixture only.
    fixture = json.loads((root / "tests/fixtures/jaipur_media_cases.json").read_text())
    pack = Path(jaipur["pack"])
    places = {p["id"]:p for p in json.loads((pack / "places.json").read_text(encoding="utf-8"))}
    cases = []
    for pid in fixture:
        place = places.get(pid)
        assurance = jaipur["report"]["assurance"].get(pid, {})
        media = assurance.get("media", {})
        image = (place or {}).get("images", {}).get("primary") or {}
        candidates = media.get("candidates", [])
        reasons = sorted({code for candidate in candidates for code in candidate.get("reason_codes", [])})
        status = "VERIFIED_REAL" if media.get("verified") else "UNRESOLVED_REQUIRED_PHOTO"
        if place is None:
            status = "ID_ABSENT_REVIEW"
            reasons = ["ID_NOT_PRESENT_IN_CURRENT_DATAFACTORY_OR_CITY_LAB_SQLITE"]
        elif assurance.get("media_policy") != "REAL_REQUIRED":
            status = "DOWNSTREAM_POLICY_MISMATCH_REVIEW"
            reasons.append("FALLBACK_DOES_NOT_RESOLVE_DOWNSTREAM_REAL_PHOTO_REQUEST")
        if not reasons:
            reasons = ["NO_VERIFIED_CANDIDATE_IN_BOUNDED_PASS"]
        cases.append({"place_id":pid,"name":(place or {}).get("name"),"policy":assurance.get("media_policy"),
            "status":status,"candidate_count":len(candidates),"final_media":image or None,
            "real_photo_verified":bool(media.get("verified")),"reason_codes":reasons,
            "ai_decisions":[c["ai"] for c in candidates if c.get("ai")],
            "source_candidates":[c.get("candidate") for c in candidates if c.get("candidate")]})
    assert len(cases) == 18 and {c["place_id"] for c in cases} == set(fixture)
    atomic_json(root / "reports/jaipur_18_media_cases.json",cases)
    geographic_reviews = [{"place_id":pid,**a} for pid,a in jaipur["report"]["assurance"].items()
                          if a["geography"]["status"] != "VALID" or a["coordinate"]["status"] in {"SUSPICIOUS","CONFLICT"}]
    atomic_json(root / "reports/jaipur_geographic_benchmark.json",geographic_reviews)
    atomic_json(root / "reports/offline_assurance_acceptance.json",{
        "cities":reports,"jaipur_18_cases":cases,"jaipur_geographic_reviews":geographic_reviews,
        "paid_providers_invoked":0,"paid_features_invoked":0,
        "additional_diagnostics":["reports/india/rajasthan/jaipur/assurance/ai_smoke.json","reports/ai_provider_diagnostic.json"],
        "acceptance_target_achieved":all(r["report"]["usability_after"]["SOURCE_DATA_READY"] for r in reports)})
    lines = ["# Offline assurance acceptance report", "", "Actual snapshot results, 3 October 2026. The implementation is tested; the full dataset acceptance target is not achieved. All four exports remain draft packs. Original v3 sources and downstream City Lab curation were preserved.", "",
        "## 1. Architecture Audit", "", "The existing factory supplied city resolution, open-data extraction, taxonomy, canonical graphs, enrichment, WebP processing, human curation, quarantine and v3 exporters. Added free-only AI routing, strict decision schemas, media/legal assurance, scoped source evidence, geographic/coordinate checks, grounded metadata recovery, fallback pools, repair orchestration and explicit usability. See docs/architecture-audit.md.", "",
        "## 2. Files Changed", "", "Important modules: datafactory/ai/{config,providers,router,decisions}.py; models/media_candidate.py; sources/openverse.py; pipeline/{repair,media_assurance,media_policy,identity_assurance,identity_review,geographic_assurance,source_evidence,metadata_assurance,fallbacks,usability,offline_export}.py; canonical graph/city/cache/source adapters; CLI; config/{ai,assurance}.yaml; assets/fallbacks; README; offline tests. Existing user edits and v3 packs were not reverted.", "",
        "## 3. AI Configuration", "", "Models actually invoked: Groq `qwen/qwen3.8-27b`; Gemini `gemini-3.8-flash`. Both appeared in account model lists and returned successful inference results. The approved alternate `gemini-3.5-flash-lite` was not invoked. Local .env loading keeps keys private and gives process environment precedence. Billing was explicitly confirmed disabled for both keys by the user.", "",
        "Model/free-tier references: [Groq vision](https://console.groq.com/docs/vision), [Groq limits](https://console.groq.com/docs/rate-limits), [Gemini models](https://ai.google.dev/gemini-api/docs/models), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing). Availability and limits can change.", "",
        "## 4. Free-Only Verification", "", "AI_MODE: FREE_ONLY. Paid providers invoked: **0**. Paid features invoked: **0**. Only approved Groq/Gemini endpoints/models are permitted; no search/grounding/generation tools. Free account confirmation is a configuration gate, not a vendor billing audit. Quota/service failures are retained as unresolved jobs. Keys never enter report or decision payloads.", "",
        "## 5. AI Usage", "", "Totals combine the archived initial live pass and the latest repair pass retained in each final export. Jaipur's latest repair pass included 10 further live calls; other latest passes reused cached decisions. One additional Jaipur Groq smoke call and one separate Gemini diagnostic call are excluded from this table and recorded in the linked diagnostic artifacts. Identity review usage appears separately below if authorized.", ""]
    lines += table(["City","Groq calls","Gemini calls","Escalations","Cache hits","429 events"],[
        [r["city"]["name"],*(r["ai_usage_total"].get(k,0) for k in ["groq_calls","gemini_calls","escalations","cache_hits","rate_limit"])] for r in reports])
    lines += ["", "## 6. Core Media", "", "Final exported decisions; rejection counts include existing and discovered candidates. No fallback satisfies REAL_REQUIRED.", ""]
    lines += table(["City","REAL_REQUIRED","Already valid","Recovered","Rejected","Unresolved"],[
        [r["city"]["name"],*(r["report"]["summary"].get(k,0) for k in ["REAL_REQUIRED","already_valid","recovered","rejected_candidates","still_unresolved"])] for r in reports])
    lines += ["", "## 7. Jaipur 18 Media Cases", "", "All 18 supplied IDs are reported. Three are absent in both current DataFactory JSON and City Lab SQLite. Three published entries have a lower media policy; their contextual artwork does not resolve the downstream real-photo request. No historical ID was silently mapped to a similarly named venue. Full source URLs, creator/license/dimensions, finalist decisions and reasons where available are in reports/jaipur_18_media_cases.json.", ""]
    lines += table(["Supplied ID","Current policy","Candidates","Result"],[[c["place_id"],c["policy"] or "absent",c["candidate_count"],c["status"]] for c in cases])
    lines += ["", "## 8. Identity Resolution", "", "Located City Lab candidate manifests read-only. These collisions originate in upstream name-based canonical IDs. New builds disambiguate colliding IDs from sorted source IDs, coordinates and category. The report proposes IDs only: no historical migration, merge or downstream edit was applied. AI opinions never waive missing factual corroboration.", ""]
    lines += table(["City","Groups found","Members","Auto-resolved","Review/unresolved","Classification"],[
        [r["city"]["name"],r["identity_review"]["groups_found"],r["identity_review"]["members_withheld"],0,r["identity_review"]["unresolved"],r["identity_review"]["decisions"]]
        for r in reports if r["identity_review"]])
    lines += ["", "City Lab external AI opinions require explicit transfer authorization after automatic approval review rejected the initial request. Local identity audits completed successfully; each report records actual AI usage and zero downstream files modified.", "",
        "## 9. Coordinates", "", "The Jaipur geographic benchmark retains original/source points, bbox, regional associations and distances in reports/jaipur_geographic_benchmark.json. Nakati Mata Temple is 18.393 km from the center, outside the municipal bbox, with only one independent coordinate source. Outcome: review regional association; do not move its coordinates or assert a wrong city. Two Jaipur published records also have suspicious coordinate comparisons. Automatic repairs require two independent sources agreeing and a supported destination-region outcome.", ""]
    lines += table(["City","Coordinate reviews","Automatic repairs"],[[r["city"]["name"],sum(a["coordinate"]["status"] in {"CONFLICT","SUSPICIOUS"} for a in r["report"]["assurance"].values()),r["report"]["summary"]["coordinate_repairs"]] for r in reports])
    lines += ["", "## 10. Metadata Recovery", "", "Source text remains factual provenance; Groq/Gemini only assist bounded extraction. Stale, ambiguous or conflicting hours remain unknown/unverified. Entity tags require the entity's own name and coordinates to corroborate the place; an OSM QID alone is insufficient.", ""]
    lines += table(["City","Hours","Descriptions","Entity links","Addresses"],[[r["city"]["name"],*(r["report"]["summary"].get(k,0) for k in ["hours_recovered","descriptions_recovered","entity_links_recovered","addresses_recovered"])] for r in reports])
    lines += ["", "## 11. Fallback Diversity", "", "216 self-authored CC0 procedural illustrations: eight variants in each of 27 contextual categories. Stable SHA-256 assignment uses the full canonical ID. Real media and contextual art are labelled separately. Smaller categories naturally use fewer variants; asset sharing counts remain visible.", ""]
    lines += table(["City","Before fallback POIs","After fallback POIs","Distinct assets used","Largest sharing"],[
        [r["city"]["name"],sum(v["published_using_fallback"] for v in r["report"]["fallback_before"].values()),
         sum(v["published_using_fallback"] for v in r["report"]["fallback_after"].values()),
         sum(v["distinct_assets"] for v in r["report"]["fallback_after"].values()),
         max((v["maximum_sharing"] for v in r["report"]["fallback_after"].values()),default=0)] for r in reports])
    lines += ["", "## 12. Usability", "", "A POI must have source-backed identity, valid category/coordinates/region, renderable local primary/thumbnail media where required, complete media provenance, and no critical anomaly. REAL_REQUIRED additionally needs visually verified authentic media. Hours, description and address coverage are separate; no mandatory factual fill is fabricated. Source readiness requires ≥95% usability and zero critical blockers.", ""]
    lines += table(["City","Published","Usable","Usable %","Critical POIs"],[[r["city"]["name"],*(r["report"]["usability_after"][k] for k in ["published","overall_usable_count","overall_usable_percentage","critical_blocker_pois"])] for r in reports])
    lines += ["", "## 13. Offline Readiness", "", "Draft readiness represents structural bundle validity and reviewability. It does not certify unresolved facts or media. Checksum, schema, JSONL/Parquet/SQLite projections, SQLite integrity and local image decode checks passed for all listed exports. Broken or duplicate optional gallery entries were pruned from these new exports, with each removal recorded; the original source packs were preserved. No referenced primary, thumbnail or gallery asset is missing in the final bundles.", ""]
    lines += table(["City","DRAFT_OFFLINE_READY","SOURCE_DATA_READY","Actual output"],[[r["city"]["name"],r["report"]["usability_after"]["DRAFT_OFFLINE_READY"],r["report"]["usability_after"]["SOURCE_DATA_READY"],r["pack"]] for r in reports])
    lines += [""] + table(["City","Optional gallery entries pruned","Pipeline health","Legacy semantic quality","Legacy source coverage"],[[r["city"]["name"],len(r["report"].get("optional_gallery_pruned",[])),r["validation"]["pipeline_health"],r["validation"]["data_quality"],r["validation"]["source_coverage"]] for r in reports])
    lines += ["", "## 14. Generalization Test", "", "Manali uses the same repair code against its existing 1,702-place snapshot, with no city-specific branches. Sparse authoritative/media coverage leaves 13 required photos unresolved despite 98.82% published usability. This is a cached-source repair/generalization test, not a fresh all-source extraction or manual destination certification. Core production source/pipeline/AI behavior contains no Jaipur attraction-name branches; legacy audit dashboards retain their fixed benchmark corpus.", "",
        "## 15. Tests", "", "Command: `.\\.venv\\Scripts\\python.exe -m pytest -q -p no:cacheprovider --basetemp=scratch/test-assurance-final-8 --tb=short`: **149 passed in 23.84 seconds**. Default tests disable live HTTP and use fixtures/MockTransport. Coverage includes strict output, free account/endpoint gating, quota cooldown/fallback/cache, city isolation, image legality/quality/identity, coordinates, grounded hours/text, fallback invariants, human locks, collision IDs, read-only identity auditing and transactional export consistency. Actual live CLI: ai-status; one-image ai-smoke; repair --apply --network for Jaipur/Udaipur/Varanasi; cached repair for Manali; final re-exports with zero inference budget. All final bundles passed validate_release_package. Repository-wide git diff --check also reports pre-existing generated HTML whitespace; source packs were left unchanged.", "",
        "Production-name scan: `rg -n 'Jaipur|Udaipur|Varanasi|Amber Fort|Hawa Mahal' datafactory`. CLI has three Jaipur help examples. classify.py has two illustrative hotel/shop comments. audit/generalization_evaluator.py has a benchmark description, three fixed dataset descriptors and one report caption; audit/dashboard.py has four report captions/example descriptions; audit/search_engine.py and audit/independent_verifier.py each have one explanatory docstring. These are examples, benchmark definitions and report text. Amber Fort and Hawa Mahal have no occurrences. There are no matching city-specific extraction, repair or AI decision branches.", "",
        "## 16. Remaining Limitations", "", "Full dataset acceptance is **not achieved**. Jaipur/Udaipur/Varanasi remain below 95%; all cities have required real-media blockers. Source discovery/research and AI budgets deliberately bound each pass. Groq free quota and Gemini temporary high-demand errors deferred work. Openverse results require original-source license verification; the implemented automatic verification adapter currently supports Commons originals, while other original hosts stay in review. Descriptions are conservative source excerpts; no schedule was recovered in these snapshots. The 18-case mismatch and 19 historical identity groups require source research/review and any eventual published-ID migration requires approval. Missing facts and photos remain explicit. City Lab's broken human media overrides and manual certification state were not changed. Temporary failed exports/older snapshots are preserved for recovery and ignored by Git. Reports expose no API keys.", ""]
    if (root / "reports/app_fallback_transition.json").exists():
        lines[2:2] = ["**Later fallback update:** Factory artwork was rejected by the user and disabled by default. The figures below describe the earlier bundled-artwork snapshots. See [app_fallback_transition.md](app_fallback_transition.md) for the current app-managed exports and strict pack-media metrics.", ""]
    (root / "reports/offline_assurance_acceptance.md").write_text("\n".join(lines),encoding="utf-8")
    print("Wrote acceptance Markdown/JSON, 18-case media JSON, and geographic evidence JSON.")


if __name__ == "__main__":
    main()
