import json
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict, Counter


def generate_core_breakdown(
    city_slug: str,
    places: List[Dict[str, Any]],
    reports_dir: Path
) -> Path:
    """
    Generates reports/<city>/core_category_breakdown.json showing:
    - category & subcategory breakdown
    - source combinations
    - travel relevance distribution
    - number with Wikidata, Wikipedia, Wikivoyage, OSM travel evidence
    - number supported only by Overture
    """
    city_reports_dir = reports_dir / city_slug
    city_reports_dir.mkdir(parents=True, exist_ok=True)
    out_file = city_reports_dir / "core_category_breakdown.json"

    core_places = [p for p in places if p.get("tier") == "core_destination"]

    cats = Counter()
    subcats = Counter()
    source_combos = Counter()
    relevance_buckets = {
        "0.0-0.2": 0,
        "0.2-0.4": 0,
        "0.4-0.6": 0,
        "0.6-0.8": 0,
        "0.8-1.0": 0,
    }

    with_wikidata = 0
    with_wikipedia = 0
    with_wikivoyage = 0
    with_osm_travel = 0
    supported_only_by_overture = 0

    for p in core_places:
        c = p.get("category", "unknown")
        sc = p.get("subcategory", "general")
        cats[c] += 1
        subcats[f"{c}/{sc}"] += 1

        sources = sorted(list(set(s.get("source") for s in p.get("sources_provenance", []))))
        source_combos[",".join(sources)] += 1

        rel = p.get("travel_relevance_score", 0.0)
        if rel < 0.2:
            relevance_buckets["0.0-0.2"] += 1
        elif rel < 0.4:
            relevance_buckets["0.2-0.4"] += 1
        elif rel < 0.6:
            relevance_buckets["0.4-0.6"] += 1
        elif rel < 0.8:
            relevance_buckets["0.6-0.8"] += 1
        else:
            relevance_buckets["0.8-1.0"] += 1

        if p.get("wikidata_id"):
            with_wikidata += 1
        if p.get("wikipedia_url"):
            with_wikipedia += 1
        if "wikivoyage" in sources:
            with_wikivoyage += 1
        if "openstreetmap" in sources:
            with_osm_travel += 1
        if sources == ["overture"]:
            supported_only_by_overture += 1

    report = {
        "city": city_slug,
        "total_core_destinations": len(core_places),
        "with_wikidata": with_wikidata,
        "with_wikipedia": with_wikipedia,
        "with_wikivoyage": with_wikivoyage,
        "with_osm_travel": with_osm_travel,
        "supported_only_by_overture": supported_only_by_overture,
        "travel_relevance_distribution": relevance_buckets,
        "categories": dict(cats.most_common()),
        "subcategories": dict(subcats.most_common()),
        "source_combinations": dict(source_combos.most_common()),
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return out_file


def generate_image_failure_breakdown(
    city_slug: str,
    places: List[Dict[str, Any]],
    reports_dir: Path
) -> Path:
    """
    Generates reports/<city>/image_failure_breakdown.json classifying
    failure reasons for all core destinations missing an image:
    - no_wikidata
    - no_P18
    - no_commons_category
    - commons_category_empty
    - wikipedia_no_image
    - license_rejected
    - download_failed
    - ambiguous_image
    - identity_confidence_too_low
    """
    city_reports_dir = reports_dir / city_slug
    city_reports_dir.mkdir(parents=True, exist_ok=True)
    out_file = city_reports_dir / "image_failure_breakdown.json"

    core_places = [p for p in places if p.get("tier") == "core_destination"]

    failure_reasons = Counter()
    failed_details = []

    for p in core_places:
        img = p.get("images", {}).get("primary") if isinstance(p.get("images"), dict) else p.get("image_metadata")
        if img:
            continue  # Image was successfully resolved

        # Determine failure reason
        qid = p.get("wikidata_id")
        p18 = p.get("wikidata_p18")
        cat = p.get("commons_category")
        wiki = p.get("wikipedia_url")
        id_conf = p.get("quality", {}).get("identity_confidence", 0.5)

        if not qid and not wiki:
            reason = "no_wikidata"
        elif qid and not p18 and not cat and not wiki:
            reason = "no_P18"
        elif cat:
            reason = "commons_category_empty"
        elif wiki:
            reason = "wikipedia_no_image"
        elif id_conf < 0.40:
            reason = "identity_confidence_too_low"
        else:
            reason = "no_P18"

        failure_reasons[reason] += 1
        failed_details.append({
            "id": p.get("id") or p.get("canonical_id"),
            "name": p.get("name"),
            "category": p.get("category"),
            "wikidata_id": qid,
            "failure_reason": reason,
        })

    total_failed = len(failed_details)
    report = {
        "city": city_slug,
        "total_core_destinations": len(core_places),
        "core_with_image": len(core_places) - total_failed,
        "core_missing_image": total_failed,
        "failure_reasons_summary": dict(failure_reasons.most_common()),
        "failed_destinations": failed_details,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return out_file
