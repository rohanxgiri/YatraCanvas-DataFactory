import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter


def audit_source_recall(
    city_name: str,
    state_name: str,
    country_name: str = "India",
    version: str = "v3",
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Audits source-by-source recall and survival of high-value travel POIs through the pipeline.
    Tracks raw candidates, matches into canonical entities, released, merged, rejected, quarantined,
    and provides top rejection reasons.
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent

    city_slug = city_name.lower().replace(" ", "_")
    state_slug = state_name.lower().replace(" ", "_")
    country_slug = country_name.lower().replace(" ", "_")

    release_dir = project_root / "releases" / country_slug / state_slug / city_slug / version
    staging_dir = project_root / "data" / "staging" / country_slug / state_slug / city_slug
    source_cache_dir = project_root / "data" / "source_cache"
    raw_dir = project_root / "data" / "raw" / country_slug / state_slug / city_slug

    # 1. Load Released Places
    places_file = release_dir / "places.json"
    released_places: List[Dict[str, Any]] = []
    if places_file.exists():
        with open(places_file, "r", encoding="utf-8") as f:
            released_places = json.load(f)

    # 2. Load Quarantined Places
    quarantine_file = staging_dir / "quarantine" / "quarantined_places.jsonl"
    quarantined_places: List[Dict[str, Any]] = []
    if quarantine_file.exists():
        with open(quarantine_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        quarantined_places.append(json.loads(line))
                    except Exception:
                        pass

    # 3. Load Rejected Places
    rejected_file = staging_dir / "rejected_places.jsonl"
    rejected_places: List[Dict[str, Any]] = []
    if rejected_file.exists():
        with open(rejected_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        rejected_places.append(json.loads(line))
                    except Exception:
                        pass

    # 4. Load Merges / Duplicates
    duplicates_file = staging_dir / "duplicates.jsonl"
    duplicates_records: List[Dict[str, Any]] = []
    if duplicates_file.exists():
        with open(duplicates_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        duplicates_records.append(json.loads(line))
                    except Exception:
                        pass

    # Track by source
    known_sources = ["openstreetmap", "overture", "wikivoyage", "wikidata", "foursquare", "alltheplaces"]
    source_stats: Dict[str, Dict[str, Any]] = {
        s: {
            "raw_candidates": 0,
            "matched_into_canonical": 0,
            "released": 0,
            "merged": 0,
            "quarantined": 0,
            "rejected": 0,
            "rejection_reasons": Counter(),
            "quarantine_reasons": Counter(),
        } for s in known_sources
    }

    # Count released by source provenance
    for p in released_places:
        p_sources = set()
        for src_item in p.get("sources", []):
            if isinstance(src_item, dict):
                s_name = src_item.get("source", "").lower()
                if s_name:
                    p_sources.add(s_name)
            elif isinstance(src_item, str):
                p_sources.add(src_item.lower())
        for prov_item in p.get("provenance_records", []):
            if isinstance(prov_item, dict):
                s_name = prov_item.get("source", "").lower()
                if s_name:
                    p_sources.add(s_name)
        ext = p.get("external_ids") or {}
        if ext.get("osm_id"):
            p_sources.add("openstreetmap")
        if ext.get("wikidata_id"):
            p_sources.add("wikidata")
        if ext.get("wikivoyage_listing_id"):
            p_sources.add("wikivoyage")
        if ext.get("overture_id"):
            p_sources.add("overture")

        for s_name in p_sources:
            if s_name not in source_stats:
                source_stats[s_name] = {
                    "raw_candidates": 0, "matched_into_canonical": 0, "released": 0,
                    "merged": 0, "quarantined": 0, "rejected": 0,
                    "rejection_reasons": Counter(), "quarantine_reasons": Counter(),
                }
            source_stats[s_name]["released"] += 1
            source_stats[s_name]["matched_into_canonical"] += 1

    # Count duplicates/merges by source
    for d in duplicates_records:
        dup_src = d.get("duplicate_source") or d.get("source") or "overture"
        dup_src = dup_src.lower()
        if dup_src not in source_stats:
            source_stats[dup_src] = {
                "raw_candidates": 0, "matched_into_canonical": 0, "released": 0,
                "merged": 0, "quarantined": 0, "rejected": 0,
                "rejection_reasons": Counter(), "quarantine_reasons": Counter(),
            }
        source_stats[dup_src]["merged"] += 1

    # Count quarantined by source
    for q in quarantined_places:
        q_src = q.get("source", "unknown").lower()
        if q_src not in source_stats:
            source_stats[q_src] = {
                "raw_candidates": 0, "matched_into_canonical": 0, "released": 0,
                "merged": 0, "quarantined": 0, "rejected": 0,
                "rejection_reasons": Counter(), "quarantine_reasons": Counter(),
            }
        source_stats[q_src]["quarantined"] += 1
        for r in q.get("reasons", ["unspecified_anomaly"]):
            source_stats[q_src]["quarantine_reasons"][r] += 1

    # Count rejected by source
    for r in rejected_places:
        r_src = r.get("source", "overture").lower()
        if r_src not in source_stats:
            source_stats[r_src] = {
                "raw_candidates": 0, "matched_into_canonical": 0, "released": 0,
                "merged": 0, "quarantined": 0, "rejected": 0,
                "rejection_reasons": Counter(), "quarantine_reasons": Counter(),
            }
        source_stats[r_src]["rejected"] += 1
        reason = r.get("rejection_reason") or r.get("reason") or "non_travel_category"
        source_stats[r_src]["rejection_reasons"][reason] += 1

    # Raw counts from manifest or calculated sum
    manifest_file = release_dir / "manifest.json"
    manifest_source_versions: Dict[str, str] = {}
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                m_data = json.load(f)
                manifest_source_versions = m_data.get("source_versions", {})
        except Exception:
            pass

    for s_name, stats in source_stats.items():
        if s_name in manifest_source_versions:
            try:
                stats["raw_candidates"] = int(manifest_source_versions[s_name])
            except (ValueError, TypeError):
                stats["raw_candidates"] = stats["released"] + stats["merged"] + stats["quarantined"] + stats["rejected"]
        else:
            stats["raw_candidates"] = stats["released"] + stats["merged"] + stats["quarantined"] + stats["rejected"]

    # -------------------------------------------------------------
    # High-Value Travel Sources Recall Evaluation
    # -------------------------------------------------------------
    # 1. Wikivoyage see/do listings survival
    wv_file = source_cache_dir / "wikivoyage" / f"{city_slug}_listings.json"
    wv_total_see_do = 0
    wv_released_see_do = 0
    wv_see_do_ids = set()
    wv_see_do_qids = set()
    wv_see_do_names = set()
    if wv_file.exists():
        try:
            with open(wv_file, "r", encoding="utf-8") as f:
                wv_listings = json.load(f)
                for item in wv_listings:
                    if item.get("listing_type") in ("see", "do"):
                        wv_total_see_do += 1
                        if item.get("source_id"):
                            wv_see_do_ids.add(item.get("source_id"))
                        if item.get("wikidata_id"):
                            wv_see_do_qids.add(item.get("wikidata_id"))
                        if item.get("name"):
                            wv_see_do_names.add(item.get("name").lower().strip())
        except Exception:
            pass

    for p in released_places:
        p_wv_id = p.get("external_ids", {}).get("wikivoyage_listing_id")
        p_qid = p.get("external_ids", {}).get("wikidata_id")
        p_name = p.get("name", "").lower().strip()
        has_wv = any(isinstance(s, dict) and s.get("source") == "wikivoyage" for s in p.get("sources", []))
        if (p_wv_id and p_wv_id in wv_see_do_ids) or (p_qid and p_qid in wv_see_do_qids) or (has_wv and p_name in wv_see_do_names):
            wv_released_see_do += 1

    # 2. Wikidata travel attractions survival
    wd_file = source_cache_dir / "wikidata" / f"{city_slug}_attractions.json"
    wd_total_attractions = 0
    wd_released_attractions = 0
    wd_qids = set()
    if wd_file.exists():
        try:
            with open(wd_file, "r", encoding="utf-8") as f:
                wd_attractions = json.load(f)
                wd_total_attractions = len(wd_attractions)
                for item in wd_attractions:
                    if item.get("wikidata_id"):
                        wd_qids.add(item.get("wikidata_id"))
        except Exception:
            pass

    for p in released_places:
        p_qid = p.get("external_ids", {}).get("wikidata_id")
        if p_qid and p_qid in wd_qids:
            wd_released_attractions += 1

    # 3. OSM Tourism / Historic POIs survival
    osm_file = raw_dir / "osm" / "places_raw.json"
    osm_total_tourism_historic = 0
    osm_th_ids = set()
    if osm_file.exists():
        try:
            with open(osm_file, "r", encoding="utf-8") as f:
                osm_data = json.load(f)
                elements = osm_data.get("elements", []) if isinstance(osm_data, dict) else (osm_data if isinstance(osm_data, list) else [])
                for item in elements:
                    tags = item.get("tags") or {}
                    if any(k in tags for k in ("tourism", "historic")):
                        osm_total_tourism_historic += 1
                        e_type = item.get("type", "node")
                        e_id = item.get("id")
                        osm_th_ids.add(f"{e_type}/{e_id}")
        except Exception:
            pass

    osm_released_travel = 0
    for p in released_places:
        p_osm_id = p.get("external_ids", {}).get("osm_id")
        if p_osm_id and p_osm_id in osm_th_ids:
            osm_released_travel += 1
        else:
            matched = False
            for s in p.get("sources", []):
                if isinstance(s, dict) and s.get("source") in ("osm", "openstreetmap"):
                    if s.get("source_id") in osm_th_ids:
                        osm_released_travel += 1
                        matched = True
                        break
            if not matched and p.get("tier") in ("core_destination", "recommended", "discovery"):
                if any(isinstance(s, dict) and s.get("source") in ("osm", "openstreetmap") for s in p.get("sources", [])):
                    osm_released_travel += 1

    high_value_survival = {
        "wikivoyage_see_do": {
            "total_raw": wv_total_see_do,
            "released": min(wv_total_see_do, wv_released_see_do),
            "survival_pct": round((min(wv_total_see_do, wv_released_see_do) / max(1, wv_total_see_do)) * 100, 1),
        },
        "wikidata_attractions": {
            "total_raw": wd_total_attractions,
            "released": min(wd_total_attractions, wd_released_attractions),
            "survival_pct": round((min(wd_total_attractions, wd_released_attractions) / max(1, wd_total_attractions)) * 100, 1),
        },
        "osm_tourism_historic": {
            "total_raw": osm_total_tourism_historic,
            "released": min(osm_total_tourism_historic, osm_released_travel),
            "survival_pct": round((min(osm_total_tourism_historic, osm_released_travel) / max(1, osm_total_tourism_historic)) * 100, 1),
        },
    }

    report = {
        "city": city_name,
        "state": state_name,
        "country": country_name,
        "version": version,
        "sources": {
            s: {
                "raw_candidates": d["raw_candidates"],
                "matched_into_canonical": d["matched_into_canonical"],
                "released": d["released"],
                "merged": d["merged"],
                "quarantined": d["quarantined"],
                "rejected": d["rejected"],
                "top_rejection_reasons": dict(d["rejection_reasons"].most_common(5)),
                "top_quarantine_reasons": dict(d["quarantine_reasons"].most_common(5)),
            } for s, d in source_stats.items() if d["raw_candidates"] > 0
        },
        "high_value_travel_survival": high_value_survival,
    }

    # Save JSON to reports/<city>/coverage/source_recall.json
    json_path = project_root / "reports" / city_slug / "coverage" / "source_recall.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report
