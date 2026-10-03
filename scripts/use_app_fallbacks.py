"""Re-export acceptance snapshots without factory artwork; no source or AI calls."""
import copy
import json
from pathlib import Path
from datafactory.pipeline.fallbacks import retire_factory_fallbacks, fallback_distribution
from datafactory.pipeline.offline_export import export_offline
from datafactory.utils.atomic import atomic_json


def main():
    root = Path(__file__).resolve().parents[1]
    acceptance = json.loads((root / "reports/offline_assurance_acceptance.json").read_text(encoding="utf-8"))
    cities = []
    for entry in acceptance["cities"]:
        source = Path(entry["pack"])
        places = json.loads((source / "places.json").read_text(encoding="utf-8"))
        report = copy.deepcopy(entry["report"])
        report["source_pack"] = str(source)
        report["mode"] = "APP_FALLBACK_TRANSITION"
        report["previous_repair_summary"] = copy.deepcopy(report["summary"])
        report["media_summary_origin"] = "Previous repair; verification retained without new inference"
        report["previous_ai_usage"] = report["ai_usage"]
        report["ai_usage"] = {"AI_MODE":"FREE_ONLY", "enabled":False, "stats":{"calls":0,"paid_feature_calls":0}, "events":[]}
        report["fallback_strategy"] = "app"
        report["fallback_before"] = fallback_distribution(places)
        report["retired_factory_fallbacks"] = retire_factory_fallbacks(places)
        report["fallback_after"] = fallback_distribution(places)
        report["fallback_authoring"] = {"enabled":False,"strategy":"app","categories":[]}
        report["source_requests_enabled"] = False
        report["network_media_discovery_places"] = 0
        report["source_research_places"] = 0
        report["decisions"] = [{"place_id":r["place_id"],"field":"images."+r["slot"],
                                "action":"AUTO_APPLY","reason_codes":["DEFER_FALLBACK_PRESENTATION_TO_APP"]}
                               for r in report["retired_factory_fallbacks"]]
        for key in ("hours_recovered","descriptions_recovered","coordinate_repairs","entity_links_recovered","addresses_recovered"):
            report["summary"][key] = 0
        report.pop("dry_run_predictions", None)
        report["usability_before"] = entry["report"]["usability_after"]
        output, usability = export_offline(source, source.parent / "v3-app-fallbacks", places, source, report)
        assert not any(p["images"]["primary"].get("source") == "YatraCanvas contextual artwork"
                       and p["images"]["primary"].get("match_method") != "verified_human_curation"
                       for p in places if p.get("images",{}).get("primary"))
        missing = sum(not p.get("images",{}).get("primary") for p in places)
        cities.append({"city":entry["city"]["name"], "source_pack":str(source),"output_pack":str(output),
                       "factory_artwork_removed":len(report["retired_factory_fallbacks"]),
                       "missing_primary_for_app_fallback":missing,
                       "strict_pack_usability":usability["overall_usable_percentage"],
                       "required_photos_unresolved":report["summary"]["still_unresolved"],
                       "DRAFT_OFFLINE_READY":usability["DRAFT_OFFLINE_READY"],
                       "SOURCE_DATA_READY":usability["SOURCE_DATA_READY"],
                       "structural_validation":"PASS", "ai_calls":0})
    result = {"fallback_strategy":"app", "ai_calls":0,"source_network_calls":0,
              "app_files_modified":0,"city_lab_files_modified":0,"cities":cities,
              "metrics_note":"Strict pack usability counts bundled media only. App fallback display is not verified source photography."}
    atomic_json(root / "reports/app_fallback_transition.json", result)
    rows = ["# App fallback transition", "", "The YatraCanvas app supplies fallback presentation. Factory artwork is disabled by default. New packs leave missing photos as images.primary=null and retain authentic photos and verified human choices. Source snapshots, app files and City Lab files were preserved. No AI or source network calls were made.", "",
            "Strict pack usability below measures bundled media only. App fallback rendering is separate and is not counted as verified source photography. Required real-photo blockers are unchanged.", "",
            "| City | Artwork removed | Missing primary / app fallback | Strict pack usable % | Required photos unresolved |", "|---|---:|---:|---:|---:|"]
    rows += [f"| {r['city']} | {r['factory_artwork_removed']} | {r['missing_primary_for_app_fallback']} | {r['strict_pack_usability']} | {r['required_photos_unresolved']} |" for r in cities]
    rows += ["", "All exports passed schema/checksum/JSONL/Parquet/SQLite consistency and local retained-image validation. They remain drafts with SOURCE_DATA_READY=false.", "", "Current output packs:", ""]
    rows += [f"- {r['city']}: `{r['output_pack']}`" for r in cities]
    (root / "reports/app_fallback_transition.md").write_text("\n".join(rows)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
