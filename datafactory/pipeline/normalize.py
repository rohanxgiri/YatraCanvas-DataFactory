import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Union, Optional
from ..config.settings import get_settings
from ..utils.text import clean_string


def run_normalize_and_filter(
    sources_or_overture: Union[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]],
    osm_places: Optional[List[Dict[str, Any]]] = None,
    rejected_output_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Normalizes raw candidates from all discovery sources (Wikivoyage, Wikidata, OSM, Overture, Foursquare),
    filters out non-travel places, and records rejected places.
    """
    settings = get_settings()
    cat_cfg = settings.categories_config
    rejection_rules = cat_cfg.get("rejection_rules", {})
    blocked_categories = set(rejection_rules.get("blocked_categories", []))
    blocked_patterns = [re.compile(p) for p in rejection_rules.get("blocked_name_patterns", [])]
    whitelist_patterns = [re.compile(p) for p in rejection_rules.get("whitelist_name_patterns", [])]

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

    def is_travel_relevant(name: str, category_hints: List[str]) -> Tuple[bool, str]:
        # Check whitelist first
        for wp in whitelist_patterns:
            if wp.search(name):
                return True, "whitelisted"

        # Check blocked categories
        for cat in category_hints:
            if not cat:
                continue
            cat_clean = cat.lower().strip().replace(" ", "_")
            if cat_clean in blocked_categories:
                return False, f"blocked_category:{cat_clean}"
            for token in cat_clean.split("_"):
                if token in blocked_categories:
                    return False, f"blocked_category_token:{token}"

        # Check blocked name patterns
        for bp in blocked_patterns:
            if bp.search(name):
                return False, "blocked_name_pattern"

        return True, "accepted"

    # 1. Wikivoyage candidates (inherently curated travel sights)
    for p in sources.get("wikivoyage", []):
        name = clean_string(p.get("name", ""))
        if not name or len(name) < 2:
            continue
        accepted_candidates.append(p)

    # 2. Wikidata candidates (curated heritage/attractions)
    for p in sources.get("wikidata", []):
        name = clean_string(p.get("name", ""))
        if not name or len(name) < 2:
            continue
        accepted_candidates.append(p)

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

        relevant, reason = is_travel_relevant(name, cat_hints)
        if not relevant:
            rejected_records.append({
                "name": name,
                "reason": reason,
                "source": "openstreetmap",
                "source_id": p.get("id"),
                "category_hints": cat_hints,
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

        relevant, reason = is_travel_relevant(name, cat_hints)
        if not relevant:
            rejected_records.append({
                "name": name,
                "reason": reason,
                "source": "overture",
                "source_id": p.get("id"),
                "category_hints": cat_hints,
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
        })

    # 5. Foursquare candidates
    for p in sources.get("foursquare", []):
        accepted_candidates.append(p)

    # 6. AllThePlaces candidates
    for p in sources.get("alltheplaces", []):
        accepted_candidates.append(p)

    # Save rejected places if path provided
    if rejected_output_path:
        rejected_output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(rejected_output_path, "w", encoding="utf-8") as f:
            for r in rejected_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[Stage 7/20] Multi-source candidate normalization & filtering:")
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


