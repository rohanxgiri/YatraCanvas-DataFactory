from typing import Dict, Any, List, Tuple, Optional
from ..utils.geo import is_point_in_bbox


CRITICAL_FIELDS = ["name", "latitude", "longitude", "category", "subcategory"]
RECOMMENDED_FIELDS = ["description", "primary_image", "opening_hours", "address"]
OPTIONAL_FIELDS = ["name_hi", "website", "phone", "wikidata_id", "wikipedia_url"]


def analyze_place_completeness(
    place: Dict[str, Any],
    city_bbox: Optional[Tuple[float, float, float, float]] = None
) -> Dict[str, Any]:
    """
    Evaluates data completeness for a single place candidate.
    Categorizes fields into critical, recommended, and optional.
    Calculates weighted completeness score in [0.0, 1.0].
    """
    missing_critical = []
    missing_recommended = []
    missing_optional = []
    present_fields = []

    # 1. Critical checks
    name = place.get("name", "").strip()
    if not name or len(name) < 2:
        missing_critical.append("name")
    else:
        present_fields.append("name")

    lat = place.get("latitude")
    lon = place.get("longitude")
    if lat is None or lon is None or not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        missing_critical.append("coordinates")
    else:
        if city_bbox and not is_point_in_bbox(lat, lon, city_bbox):
            missing_critical.append("coordinates_outside_city_bbox")
        else:
            present_fields.append("coordinates")

    cat = place.get("category", "")
    subcat = place.get("subcategory", "")
    if not cat or cat in ("unknown", "unclassified"):
        missing_critical.append("category")
    else:
        present_fields.append("category")

    if not subcat or subcat in ("unclassified", "general_poi", "unknown"):
        missing_critical.append("subcategory")
    else:
        present_fields.append("subcategory")

    tier = place.get("tier", "discovery")

    # 2. Tier- and Category-Aware Recommended checks
    # Nature, viewpoints, ghats, and stepwells typically do not have scheduled opening hours
    hours_applicable = cat not in ("nature", "viewpoint") and subcat not in ("lake", "waterfall", "scenic_viewpoint", "ghat", "stepwell")
    # Support tier POIs (hotels, transport) do not require encyclopedic descriptions
    desc_applicable = tier in ("core_destination", "recommended")

    if place.get("description"):
        present_fields.append("description")
    elif desc_applicable:
        missing_recommended.append("description")
    else:
        missing_optional.append("description")

    has_img = False
    if place.get("images") and isinstance(place["images"], dict):
        has_img = bool(place["images"].get("primary"))
    elif place.get("primary_image") or place.get("wikidata_p18") or place.get("commons_image"):
        has_img = True

    if has_img:
        present_fields.append("primary_image")
    else:
        missing_recommended.append("primary_image")

    raw_hours = place.get("opening_hours")
    if not raw_hours and isinstance(place.get("opening_hours_record"), dict):
        raw_hours = place["opening_hours_record"].get("raw")
    if raw_hours:
        present_fields.append("opening_hours")
    elif hours_applicable:
        missing_recommended.append("opening_hours")
    else:
        missing_optional.append("opening_hours")

    if place.get("address"):
        present_fields.append("address")
    else:
        missing_recommended.append("address")

    # 3. Optional checks
    if place.get("name_hi"):
        present_fields.append("name_hi")
    else:
        missing_optional.append("name_hi")

    if place.get("website"):
        present_fields.append("website")
    else:
        missing_optional.append("website")

    if place.get("phone"):
        present_fields.append("phone")
    else:
        missing_optional.append("phone")

    if place.get("wikidata_id"):
        present_fields.append("wikidata_id")
    else:
        missing_optional.append("wikidata_id")

    if place.get("wikipedia_url"):
        present_fields.append("wikipedia_url")
    else:
        missing_optional.append("wikipedia_url")

    # Weighted score calculation:
    # Critical: 50%
    # Recommended: 35%
    # Optional: 15%
    num_crit_total = 4  # name, coord, cat, subcat
    crit_ratio = max(0.0, (num_crit_total - len(missing_critical)) / num_crit_total)

    num_rec_total = max(1, len(missing_recommended) + sum(1 for f in ["description", "primary_image", "opening_hours", "address"] if f in present_fields and ((f != "description" or desc_applicable) and (f != "opening_hours" or hours_applicable))))
    rec_present = sum(1 for f in ["description", "primary_image", "opening_hours", "address"] if f in present_fields and ((f != "description" or desc_applicable) and (f != "opening_hours" or hours_applicable)))
    rec_ratio = max(0.0, min(1.0, rec_present / num_rec_total))

    num_opt_total = max(1, len(missing_optional) + len([f for f in present_fields if f not in ["name", "coordinates", "category", "subcategory"] and f not in ["primary_image", "address"] and (f != "description" or not desc_applicable) and (f != "opening_hours" or not hours_applicable)]))
    opt_present = len([f for f in present_fields if f not in ["name", "coordinates", "category", "subcategory"] and f not in ["primary_image", "address"] and (f != "description" or not desc_applicable) and (f != "opening_hours" or not hours_applicable)])
    opt_ratio = max(0.0, min(1.0, opt_present / num_opt_total))

    score = round((0.50 * crit_ratio) + (0.35 * rec_ratio) + (0.15 * opt_ratio), 3)

    return {
        "completeness_score": score,
        "is_complete_critical": len(missing_critical) == 0,
        "missing_critical": missing_critical,
        "missing_recommended": missing_recommended,
        "missing_optional": missing_optional,
        "present_fields": present_fields,
        "needs_enrichment": len(missing_recommended) > 0 or not place.get("wikidata_id"),
    }



def run_completeness_analysis(
    places: List[Dict[str, Any]],
    city_bbox: Optional[Tuple[float, float, float, float]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Evaluates completeness across all candidates before enrichment.
    Attaches 'completeness' metadata to each place and aggregates city-wide metrics.
    """
    total = len(places)
    if total == 0:
        return places, {
            "total_places": 0,
            "avg_completeness": 0.0,
            "with_description_pct": 0.0,
            "with_primary_image_pct": 0.0,
            "with_opening_hours_pct": 0.0,
            "with_bilingual_name_pct": 0.0,
            "with_contact_pct": 0.0,
        }

    scored_places = []
    sum_score = 0.0
    with_desc = 0
    with_img = 0
    with_hours = 0
    with_bilingual = 0
    with_contact = 0

    for p in places:
        res = analyze_place_completeness(p, city_bbox)
        item = dict(p)
        item["completeness"] = res
        scored_places.append(item)

        sum_score += res["completeness_score"]
        if "description" in res["present_fields"]:
            with_desc += 1
        if "primary_image" in res["present_fields"]:
            with_img += 1
        if "opening_hours" in res["present_fields"]:
            with_hours += 1
        if "name_hi" in res["present_fields"]:
            with_bilingual += 1
        if "website" in res["present_fields"] or "phone" in res["present_fields"]:
            with_contact += 1

    summary = {
        "total_places": total,
        "avg_completeness": round(sum_score / total, 3),
        "with_description_pct": round((with_desc / total) * 100, 1),
        "with_primary_image_pct": round((with_img / total) * 100, 1),
        "with_opening_hours_pct": round((with_hours / total) * 100, 1),
        "with_bilingual_name_pct": round((with_bilingual / total) * 100, 1),
        "with_contact_pct": round((with_contact / total) * 100, 1),
    }

    return scored_places, summary
