import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Union, Optional
from ..config.settings import get_settings
from ..utils.text import clean_string
from .travel_relevance import prefilter_candidate


def run_normalize_and_filter(
    sources_or_overture: Union[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]],
    osm_places: Optional[List[Dict[str, Any]]] = None,
    rejected_output_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    STAGE 1: Candidate Normalization and Fast Relevance Prefilter.
    Normalizes raw candidates from all sources (Wikivoyage, Wikidata, OSM, Overture, Foursquare),
    immediately excludes high-confidence non-travel junk (banks, ATMs, offices, clinics, apartments),
    and tags remaining candidates as TRAVEL_CANDIDATE, SECONDARY_TRAVEL_CANDIDATE, or REVIEW_CANDIDATE.
    """
    settings = get_settings()
    cat_cfg = settings.categories_config

    rejected_records = []
    accepted_candidates = []

    # Unpack sources dictionary or legacy overture/osm lists
    sources: Dict[str, List[Dict[str, Any]]] = {}
    if isinstance(sources_or_overture, dict):
        sources = sources_or_overture
    else:
        sources["overture"] = sources_or_overture or []
        if osm_places:
            sources["openstreetmap"] = osm_places

    # 1. Wikivoyage candidates
    for p in sources.get("wikivoyage", []):
        name = clean_string(p.get("name", ""))
        if not name or len(name) < 2:
            continue

        stage, reason, ev = prefilter_candidate(p, cat_cfg)
        if stage == "EXCLUDE":
            rejected_records.append({
                "name": name,
                "decision": "EXCLUDE",
                "reason_code": reason,
                "source": "wikivoyage",
                "source_id": p.get("id") or p.get("listing_id"),
                "evidence": ev,
            })
            continue

        item = dict(p)
        wv_id = p.get("source_id") or p.get("id") or p.get("listing_id")
        item["sources_provenance"] = [{
            "source": "wikivoyage",
            "source_id": wv_id,
            "retrieved_at": p.get("retrieved_at"),
        }]
        item["wikivoyage_listing_id"] = wv_id
        item["relevance_stage1"] = stage
        item["relevance_reason1"] = reason
        accepted_candidates.append(item)

    # 2. Wikidata candidates (Must pass prefilter! No unconditional acceptance)
    for p in sources.get("wikidata", []):
        name = clean_string(p.get("name", ""))
        if not name or len(name) < 2:
            continue

        stage, reason, ev = prefilter_candidate(p, cat_cfg)
        if stage == "EXCLUDE":
            rejected_records.append({
                "name": name,
                "decision": "EXCLUDE",
                "reason_code": reason,
                "source": "wikidata",
                "source_id": p.get("wikidata_id") or p.get("source_id"),
                "evidence": ev,
            })
            continue

        item = dict(p)
        item["sources_provenance"] = [{
            "source": "wikidata",
            "source_id": p.get("wikidata_id") or p.get("source_id") or p.get("id"),
            "retrieved_at": p.get("retrieved_at"),
        }]
        item["relevance_stage1"] = stage
        item["relevance_reason1"] = reason
        accepted_candidates.append(item)

    # 3. OSM candidates
    for p in sources.get("openstreetmap", []):
        name = clean_string(p.get("name", ""))
        if not name or len(name) < 2:
            continue

        tags = p.get("tags", {})
        cat_hints = [
            tags.get("tourism"),
            tags.get("historic"),
            tags.get("amenity"),
            tags.get("leisure"),
            tags.get("natural"),
            tags.get("shop"),
        ]
        cat_hints = [c for c in cat_hints if c]

        candidate_obj = {
            "name": name,
            "source": "openstreetmap",
            "tags": tags,
            "category_hints": cat_hints,
        }

        stage, reason, ev = prefilter_candidate(candidate_obj, cat_cfg)
        if stage == "EXCLUDE":
            rejected_records.append({
                "name": name,
                "decision": "EXCLUDE",
                "reason_code": reason,
                "source": "openstreetmap",
                "source_id": p.get("id"),
                "evidence": ev,
            })
            continue

        accepted_candidates.append({
            "source": "openstreetmap",
            "source_id": p.get("id"),
            "name": name,
            "name_en": p.get("name_en") or name,
            "name_hi": p.get("name_hi"),
            "alternate_names": [clean_string(a) for a in p.get("alternate_names", []) if a],
            "latitude": p.get("latitude"),
            "longitude": p.get("longitude"),
            "raw_category": cat_hints[0] if cat_hints else "unknown",
            "category_hints": cat_hints,
            "website": p.get("website"),
            "phone": p.get("phone"),
            "address": p.get("address"),
            "confidence": 0.85,
            "sources_provenance": [{"source": "openstreetmap", "source_id": p.get("id")}],
            "wikidata_id": p.get("wikidata_id") or p.get("wikidata"),
            "wikipedia_url": p.get("wikipedia_url") or p.get("wikipedia"),
            "opening_hours": p.get("opening_hours"),
            "tags": tags,
            "osm_tags": tags,
            "relevance_stage1": stage,
            "relevance_reason1": reason,
        })

    # 4. Overture candidates
    for p in sources.get("overture", []):
        name = clean_string(p.get("name", ""))
        if not name or len(name) < 2:
            continue

        cat_hints = []
        if p.get("basic_category"):
            cat_hints.append(p["basic_category"])
        if p.get("taxonomy") and isinstance(p["taxonomy"], dict):
            cat_hints.append(p["taxonomy"].get("primary"))
        if p.get("categories") and isinstance(p["categories"], dict):
            cat_hints.append(p["categories"].get("primary"))

        hierarchies = []
        if p.get("taxonomy") and isinstance(p["taxonomy"], dict):
            hierarchies = p["taxonomy"].get("hierarchy") or []

        candidate_obj = {
            "name": name,
            "source": "overture",
            "category_hints": cat_hints,
            "taxonomy_hierarchy": hierarchies,
            "tags": {},
        }

        stage, reason, ev = prefilter_candidate(candidate_obj, cat_cfg)
        if stage == "EXCLUDE":
            rejected_records.append({
                "name": name,
                "decision": "EXCLUDE",
                "reason_code": reason,
                "source": "overture",
                "source_id": p.get("id"),
                "evidence": ev,
            })
            continue

        accepted_candidates.append({
            "source": "overture",
            "source_id": p.get("id"),
            "name": name,
            "alternate_names": [clean_string(a) for a in p.get("alternate_names", []) if a],
            "latitude": p.get("latitude"),
            "longitude": p.get("longitude"),
            "raw_category": cat_hints[0] if cat_hints else "unknown",
            "category_hints": cat_hints,
            "website": p.get("website"),
            "phone": p.get("phone"),
            "address": p.get("address"),
            "confidence": p.get("confidence", 0.5),
            "sources_provenance": [{"source": "overture", "source_id": p.get("id")}],
            "wikidata_id": None,
            "wikipedia_url": None,
            "opening_hours": None,
            "relevance_stage1": stage,
            "relevance_reason1": reason,
        })

    # 5. Foursquare candidates
    for p in sources.get("foursquare", []):
        name = clean_string(p.get("name", ""))
        if not name or len(name) < 2:
            continue
        stage, reason, ev = prefilter_candidate(p, cat_cfg)
        if stage == "EXCLUDE":
            rejected_records.append({
                "name": name,
                "decision": "EXCLUDE",
                "reason_code": reason,
                "source": "foursquare",
                "source_id": p.get("id"),
                "evidence": ev,
            })
            continue
        item = dict(p)
        item["relevance_stage1"] = stage
        item["relevance_reason1"] = reason
        accepted_candidates.append(item)

    # 6. AllThePlaces candidates
    for p in sources.get("alltheplaces", []):
        name = clean_string(p.get("name", ""))
        if not name or len(name) < 2:
            continue
        stage, reason, ev = prefilter_candidate(p, cat_cfg)
        if stage == "EXCLUDE":
            rejected_records.append({
                "name": name,
                "decision": "EXCLUDE",
                "reason_code": reason,
                "source": "alltheplaces",
                "source_id": p.get("id"),
                "evidence": ev,
            })
            continue
        item = dict(p)
        item["relevance_stage1"] = stage
        item["relevance_reason1"] = reason
        accepted_candidates.append(item)

    # Save rejected places if path provided
    if rejected_output_path:
        rejected_output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(rejected_output_path, "w", encoding="utf-8") as f:
            for r in rejected_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[Stage 7/20] STAGE 1 Fast Relevance Prefilter complete:")
    print(f"       Accepted candidates: {len(accepted_candidates)}")
    print(f"       Rejected non-travel records: {len(rejected_records)}")

    return accepted_candidates


def run_normalize(
    raw_candidates: Union[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]],
    city_bbox: Optional[Tuple[float, float, float, float]] = None,
    rejected_output_path: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Convenience wrapper for CLI calling candidate normalization and returning (accepted, rejected_count).
    """
    accepted = run_normalize_and_filter(raw_candidates, rejected_output_path=rejected_output_path)
    rejected_count = 0
    if rejected_output_path and rejected_output_path.exists():
        with open(rejected_output_path, "r", encoding="utf-8") as f:
            rejected_count = sum(1 for _ in f)
    return accepted, rejected_count
