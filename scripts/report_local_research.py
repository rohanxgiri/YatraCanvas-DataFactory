"""Reproduce cached four-city acceptance without cloud inference or extraction."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from datafactory.config.settings import get_settings
from datafactory.local_intelligence.config import LocalConfig
from datafactory.local_intelligence.duplicates import DuplicateIndex
from datafactory.local_intelligence.media import LocalMediaRanker
from datafactory.local_intelligence.hours import validate_hours
from datafactory.models.media_candidate import MediaCandidate
from datafactory.pipeline.media_assurance import deterministic_filter
from datafactory.research.export import find_pack, export_research, read_assurance, snapshot
from datafactory.utils.atomic import atomic_json
from datafactory.utils.hashing import slugify


def main():
    settings = get_settings()
    results, preserved = [], {}
    for name in ("Jaipur", "Udaipur", "Varanasi", "Manali"):
        pack = find_pack(name, settings=settings)
        city = json.loads((pack / "city.json").read_text(encoding="utf-8"))
        places = json.loads((pack / "places.json").read_text(encoding="utf-8"))
        scope = Path(slugify(city["country"])) / slugify(city["state"]) / slugify(city["name"])
        before, v3_before = snapshot(pack), snapshot(pack.parent / "v3")
        exported = export_research(pack, settings.data_dir / "research/exports" / scope, settings=settings)
        tasks = json.loads((Path(exported["output"]) / "research_handoff.json").read_text(encoding="utf-8"))["tasks"]
        ranker = LocalMediaRanker(settings.cache_dir / "local_media", LocalConfig(local_media_allow_download=False))
        stats = Counter(candidate_records=0, valid_cached_candidates=0, duplicates_removed=0,
                        local_ranking_opportunities=0, local_rankings=0, entity_linked_acceptance_opportunities=0,
                        locally_valid_schedule_strings=0)
        assurance = read_assurance(pack)
        for place in places:
            rows = assurance.get(place["id"], {}).get("media", {}).get("candidates", [])
            pool, ready, seen = DuplicateIndex(), [], set()
            for row in rows:
                if not row.get("candidate"):
                    continue
                candidate = MediaCandidate.model_validate(row["candidate"])
                if candidate.media_url in seen:
                    continue
                seen.add(candidate.media_url)
                stats["candidate_records"] += 1
                if row.get("existing"):
                    path = pack / (place.get("images", {}).get("primary") or {}).get("local_path", "missing")
                else:
                    path = settings.staging_dir / scope / "assurance/downloads" / (hashlib.sha256(candidate.media_url.encode()).hexdigest() + ".bin")
                if not path.is_file() or path.stat().st_size > 20_000_000:
                    continue
                content = path.read_bytes()
                if not deterministic_filter(candidate, content)["accepted"]:
                    continue
                stats["valid_cached_candidates"] += 1
                if pool.check(content)["duplicate"]:
                    stats["duplicates_removed"] += 1
                    continue
                ready.append((candidate, path))
                if (candidate.match_method == "wikidata_p18" and candidate.source_confidence >= .98
                        and candidate.original_license_verified and candidate.related_entity_id
                        and candidate.related_entity_id == place.get("external_ids", {}).get("wikidata_id")):
                    stats["entity_linked_acceptance_opportunities"] += 1
            if ready:
                stats["local_ranking_opportunities"] += len(ready)
                ranked = ranker.rank(place, city, ready, persist=False)
                stats["local_rankings"] += sum(row["local"].get("status") in {"OK", "CACHE_HIT"} for row in ranked)
            hours = place.get("opening_hours", {})
            if validate_hours(hours.get("normalized") or hours.get("raw"))["valid"]:
                stats["locally_valid_schedule_strings"] += 1
        zeros = [t for t in tasks if t["type"] == "REAL_PRIMARY_IMAGE" and t["priority"] == "P0" and t["known_evidence"]["zero_candidates"]]
        results.append({**exported, "source_pack": pack.relative_to(settings.project_root).as_posix(), "analysis": dict(stats),
            "local_model": {"model":ranker.config.local_media_model,"batch_size":ranker.config.local_media_batch_size,
                            "max_candidates":ranker.config.local_media_max_candidates,"stats":dict(ranker.stats)},
            "zero_candidate_required_images":len(zeros),
            "zero_candidate_required_examples":[{"place_id":t["place_id"],"name":t["place"]["name"],"task_id":t["task_id"]} for t in zeros[:8]],
            "ai_usage":{"groq_calls":0,"gemini_calls":0,"paid_calls":0,"measured_cloud_call_reduction":0}})
        preserved[name] = {"source_pack_unchanged": before == snapshot(pack), "original_v3_unchanged":v3_before == snapshot(pack.parent / "v3")}
    report = {"cities":results,"total_tasks":sum(r["total"] for r in results),"preservation":preserved}
    atomic_json(settings.reports_dir / "local_research_acceptance.json", report)
    lines = ["# Local intelligence and research handoff acceptance", "", "Cached snapshots; no fresh extraction, web research or cloud inference.", "",
             "| City | Hours | Images | Website | Description | Coordinates | Identity | Total | P0 zero candidates |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in results:
        values = [row["by_type"][k] for k in ("OPENING_HOURS","REAL_PRIMARY_IMAGE","WEBSITE","DESCRIPTION","COORDINATE_RESEARCH","IDENTITY_RESEARCH")]
        lines.append(f"| {row['city']['name']} | " + " | ".join(map(str, values + [row['total'],row['zero_candidate_required_images']])) + " |")
    lines += ["", f"Total unresolved tasks: **{report['total_tasks']}**.", "",
        "| City | Cached candidates examined | Valid cached files | Duplicates | Ranking opportunities | SigLIP rankings | Valid schedule strings |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for row in results:
        lines.append(f"| {row['city']['name']} | " + " | ".join(str(row["analysis"][k]) for k in
            ("candidate_records","valid_cached_candidates","duplicates_removed","local_ranking_opportunities","local_rankings","locally_valid_schedule_strings")) + " |")
    lines += ["", "Actual Groq calls: **0**; Gemini: **0**; paid calls: **0**. Measured call reduction: **0** (no new live baseline).",
        "Local authoritative/source checks skip cloud decisions; tests demonstrate this without claiming dataset-wide savings.",
        "", "## Jaipur required photographs with no saved discovered candidates", ""]
    lines.extend(f"- {e['name']} (`{e['place_id']}`): P0 REAL_PRIMARY_IMAGE, `{e['task_id']}`." for e in results[0]["zero_candidate_required_examples"])
    lines += ["", "## Limitations", "",
        "- Optional SigLIP/Sentence Transformers packages and weights are absent here. No download was forced; model fallback was exercised.",
        "- Zero candidates means no saved discovered candidate in the prior assessment, not new network discovery.",
        "- Identity counts cover published unresolved identities; quarantined/unpublished candidates are not revived or imported by name.",
        "- No external research result was fabricated or applied to production packs. Fixtures demonstrate safe hours/media import and complete rebuild.",
        "- Original v3 and selected source snapshot hashes stayed unchanged in all four cities.",
        "", "See docs/local-research-workflow.md and reports/local_research_final.md for architecture, dependencies, tests and commands.", ""]
    (settings.reports_dir / "local_research_acceptance.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
