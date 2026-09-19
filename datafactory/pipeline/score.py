from typing import Dict, Any, List, Tuple
from ..config.settings import get_settings
from ..utils.geo import is_point_in_bbox, haversine_distance_meters


def run_score(
    places: List[Dict[str, Any]],
    city_bbox: Tuple[float, float, float, float]
) -> List[Dict[str, Any]]:
    """
    Computes explainable field-level confidence scores, overall quality scores,
    travel relevance scores, prominence scores, anomaly scores, and heuristic planning metadata.
    Enforces strict core-destination de-inflation.
    """
    settings = get_settings()
    q_cfg = settings.quality_config
    weights = q_cfg.get("weights", {
        "identity_confidence": 0.30,
        "coordinate_confidence": 0.20,
        "image_confidence": 0.25,
        "metadata_completeness": 0.25
    })
    plan_cfg = settings.planning_defaults_config.get("category_defaults", {})
    default_plan = settings.planning_defaults_config.get("default_fallback", {})

    scored_places = []
    demoted_core_count = 0

    for p in places:
        item = dict(p)
        sources = [s.get("source") for s in item.get("sources_provenance", [])]
        num_sources = len(item.get("sources_provenance", []))
        name = item.get("name", "")
        name_lower = name.lower()
        cat = item.get("category", "experience")
        subcat = item.get("subcategory")
        current_tier = item.get("tier", "discovery")

        # -------------------------------------------------------------
        # 1. Field-Level Confidence Calculation & Evidence Tracking
        # -------------------------------------------------------------
        evidence: Dict[str, str] = {}

        # A. Identity Confidence
        id_score = 0.20
        id_ev = "Single unverified source"
        if item.get("wikidata_id") and item.get("wikipedia_url"):
            id_score = 1.0
            id_ev = f"Verified across Wikidata ({item['wikidata_id']}) and Wikipedia"
        elif item.get("wikidata_id"):
            id_score = 0.90
            id_ev = f"Linked to verified Wikidata QID: {item['wikidata_id']}"
        elif item.get("commons_image"):
            id_score = 0.85
            id_ev = "Verified with Wikimedia Commons listing"
        elif "openstreetmap" in sources and num_sources > 1:
            id_score = 0.80
            id_ev = "Multi-source agreement with OpenStreetMap"
        elif "wikivoyage" in sources:
            id_score = 0.75
            id_ev = "Direct Wikivoyage travel listing"
        elif num_sources > 1:
            id_score = 0.65
            id_ev = f"Multi-source confirmation across {num_sources} providers"
        elif item.get("website"):
            id_score = 0.45
            id_ev = "Single source with official website"
        evidence["identity"] = id_ev

        # B. Name Confidence
        name_score = 0.60
        name_ev = "Source name"
        if item.get("name_hi") and item.get("name_en"):
            name_score = 1.0
            name_ev = "Bilingual English and Hindi names verified"
        elif item.get("wikidata_id") or "wikivoyage" in sources:
            name_score = 0.90
            name_ev = "Curated travel catalog label"
        elif num_sources > 1:
            name_score = 0.85
            name_ev = "Confirmed across multiple providers"
        elif "openstreetmap" in sources:
            name_score = 0.75
            name_ev = "OpenStreetMap tag name"
        evidence["name"] = name_ev

        # C. Coordinate Confidence
        lat = item.get("latitude")
        lon = item.get("longitude")
        coord_score = 0.50
        coord_ev = "Single source coordinates"
        if lat is not None and lon is not None:
            in_bbox = is_point_in_bbox(lat, lon, city_bbox)
            if in_bbox:
                if num_sources > 1:
                    coord_score = 1.0
                    coord_ev = "Multi-source spatial agreement within city boundary"
                elif "openstreetmap" in sources or item.get("wikidata_id"):
                    coord_score = 0.90
                    coord_ev = "High-precision OSM/Wikidata node within city boundary"
                else:
                    coord_score = 0.75
                    coord_ev = "Verified within city boundary"
            else:
                coord_score = 0.20
                coord_ev = "Coordinates fall outside canonical city boundary"
        evidence["coordinates"] = coord_ev

        # D. Category Confidence
        cat_conf = item.get("category_confidence", 0.60)
        votes = item.get("category_votes", [])
        if any(v.get("source") in ("wikidata", "openstreetmap") for v in votes):
            cat_ev = f"Structured {cat}/{subcat} backed by authoritative tags"
        elif any(v.get("source") == "wikivoyage" for v in votes):
            cat_ev = f"Travel listing classification ({cat}/{subcat})"
        elif votes:
            cat_ev = f"Category voting winner ({cat}/{subcat}) with weight {cat_conf}"
        else:
            cat_ev = "Heuristic fallback"
        evidence["category"] = cat_ev

        # E. Image Confidence
        img_meta = item.get("image_metadata")
        img_score = 0.0
        img_ev = "No verified image (zero generic placeholder policy)"
        if img_meta:
            method = img_meta.get("match_method")
            if method == "wikidata_p18":
                img_score = 1.0
                img_ev = "Exact Wikidata P18 verified image"
            elif method == "wikivoyage_listing_image":
                img_score = 0.95
                img_ev = "Exact Wikivoyage Commons listing image"
            elif method == "commons_category":
                img_score = 0.85
                img_ev = "Wikidata Commons category verified lead image"
            elif method == "wikipedia_lead_image":
                img_score = 0.80
                img_ev = "Linked Wikipedia article lead image"
            else:
                img_score = 0.65
                img_ev = f"Verified Commons image via {method}"
        evidence["image"] = img_ev

        # F. Opening Hours Confidence
        hours_score = 0.0
        hours_ev = "No opening hours available from open sources"
        if item.get("opening_hours"):
            h_src = item.get("opening_hours_source", "unknown")
            if h_src == "openstreetmap":
                hours_score = 0.90
                hours_ev = "Structured OSM opening_hours specification"
            elif h_src == "wikivoyage":
                hours_score = 0.85
                hours_ev = "Structured Wikivoyage hours parameter"
            else:
                hours_score = 0.70
                hours_ev = f"Structured hours from {h_src}"
        evidence["opening_hours"] = hours_ev

        field_confidence = {
            "identity_confidence": round(id_score, 2),
            "name_confidence": round(name_score, 2),
            "coordinate_confidence": round(coord_score, 2),
            "category_confidence": round(cat_conf, 2),
            "image_confidence": round(img_score, 2),
            "opening_hours_confidence": round(hours_score, 2),
            "evidence": evidence,
        }

        # -------------------------------------------------------------
        # 2. Metadata Completeness & Overall Quality
        # -------------------------------------------------------------
        meta_score = 0.0
        if item.get("opening_hours"):
            meta_score += 0.30
        if item.get("website"):
            meta_score += 0.25
        if item.get("phone"):
            meta_score += 0.15
        if item.get("address"):
            meta_score += 0.15
        if item.get("alternate_names") and len(item["alternate_names"]) > 0:
            meta_score += 0.15
        meta_score = min(1.0, round(meta_score, 2))

        overall = (
            id_score * weights.get("identity_confidence", 0.30) +
            coord_score * weights.get("coordinate_confidence", 0.20) +
            img_score * weights.get("image_confidence", 0.25) +
            meta_score * weights.get("metadata_completeness", 0.25)
        )
        overall = min(1.0, round(overall, 3))

        item["quality"] = {
            "overall": overall,
            "identity_confidence": round(id_score, 2),
            "coordinate_confidence": round(coord_score, 2),
            "image_confidence": round(img_score, 2),
            "metadata_completeness": round(meta_score, 2),
            "field_confidence": field_confidence,
        }

        # -------------------------------------------------------------
        # 3. Anomaly Detection Engine
        # -------------------------------------------------------------
        anomaly_score = 0.0
        anomaly_flags = []

        # A. Semantic dissonance: lake with palace or station
        if cat == "nature" and subcat == "lake":
            if any(w in name_lower for w in ["palace", "hotel", "resort", "station", "junction"]):
                anomaly_score += 0.40
                anomaly_flags.append("category_lake_with_palace_or_transit_keyword")

        # B. Heritage with lodging terms
        if cat == "heritage":
            if any(w in name_lower for w in ["hotel", "oyo", "resort", "inn", "guest house", "marriage garden"]):
                anomaly_score += 0.35
                anomaly_flags.append("category_heritage_with_lodging_keyword")

        # C. Single source Overture claiming core destination
        if current_tier == "core_destination" and num_sources == 1 and "overture" in sources:
            if not item.get("wikidata_id") and not item.get("heritage"):
                anomaly_score += 0.30
                anomaly_flags.append("single_source_overture_in_core")

        # D. Weak coordinate confidence
        if coord_score < 0.40:
            anomaly_score += 0.25
            anomaly_flags.append("coordinates_outside_city_bbox")

        # E. Low identity confidence in core
        if current_tier == "core_destination" and id_score < 0.40:
            anomaly_score += 0.20
            anomaly_flags.append("low_identity_confidence_in_core")

        item["anomaly_score"] = min(1.0, round(anomaly_score, 2))
        item["anomaly_flags"] = anomaly_flags

        # -------------------------------------------------------------
        # 4. Strict Core Destination De-Inflation Filter
        # -------------------------------------------------------------
        if current_tier == "core_destination":
            # Demote if supported only by single commercial source with no strong travel signals
            has_strong_signal = (
                bool(item.get("wikidata_id")) or
                bool(item.get("heritage")) or
                "wikivoyage" in sources or
                ("openstreetmap" in sources and cat in ("heritage", "museum")) or
                (num_sources >= 2 and cat in ("heritage", "museum", "arts_culture"))
            )

            is_commercial = any(w in name_lower for w in [
                "hotel", "oyo", "resort", "inn", "guest house", "marriage garden",
                "colony", "apartment", "apartments", "store", "shop", "dry cleaners"
            ])

            if not has_strong_signal or is_commercial:
                demoted_core_count += 1
                if cat in ("hotel", "transport"):
                    item["tier"] = "support"
                elif cat in ("food", "cafe", "shopping", "park", "religious"):
                    item["tier"] = "recommended"
                else:
                    item["tier"] = "discovery"

        # -------------------------------------------------------------
        # 5. Explainable Travel Relevance Score
        # -------------------------------------------------------------
        relevance = 0.0
        if "wikivoyage" in sources:
            relevance += 0.35
        elif item.get("tier") == "core_destination":
            relevance += 0.30
        if item.get("wikidata_id"):
            relevance += 0.25
        if item.get("wikipedia_url"):
            relevance += 0.15
        if img_meta:
            relevance += 0.15
        if num_sources > 1:
            relevance += 0.10
        if item.get("website"):
            relevance += 0.05
        if item.get("opening_hours"):
            relevance += 0.05
        item["travel_relevance_score"] = min(1.0, round(relevance, 2))

        # -------------------------------------------------------------
        # 6. Prominence Score
        # -------------------------------------------------------------
        tier = item.get("tier", "discovery")
        base_prominence = 0.30
        if tier == "core_destination":
            base_prominence = 0.85
        elif tier == "recommended":
            base_prominence = 0.60
        elif tier == "support":
            base_prominence = 0.50

        if item.get("wikidata_id"):
            base_prominence += 0.10
        if img_meta:
            base_prominence += 0.05
        item["prominence_score"] = min(1.0, round(base_prominence, 2))

        # -------------------------------------------------------------
        # 7. Planning Metadata
        # -------------------------------------------------------------
        cat_plan = plan_cfg.get(cat, default_plan)
        sub_plan = cat_plan.get("subcategories", {}).get(subcat, {})

        rec_mins = sub_plan.get("recommended_visit_minutes") or cat_plan.get("recommended_visit_minutes", default_plan.get("recommended_visit_minutes", 60))
        base_priority = sub_plan.get("tourism_priority") or cat_plan.get("tourism_priority", default_plan.get("tourism_priority", 0.50))

        if tier == "core_destination":
            base_priority = max(base_priority, 0.80)
        elif tier == "recommended":
            base_priority = max(base_priority, 0.60)

        priority = min(0.99, round(base_priority, 2))

        indoor_outdoor = "both"
        if subcat in ("fort", "park", "garden", "lake", "viewpoint", "ghat", "stepwell", "nature_reserve"):
            indoor_outdoor = "outdoor"
        elif subcat in ("museum", "theatre", "cinema", "coffee_shop", "restaurant", "hotel"):
            indoor_outdoor = "indoor"

        tags = set(item.get("tags", []))
        if sub_plan.get("tags"):
            tags.update(sub_plan["tags"])
        elif cat_plan.get("tags"):
            tags.update(cat_plan["tags"])

        item["planning"] = {
            "recommended_visit_minutes": rec_mins,
            "visit_duration_source": "category_heuristic",
            "rule_version": "3.0",
            "tourism_priority": priority,
            "planning_priority": priority,
            "indoor_outdoor": indoor_outdoor,
            "interest_tags": sorted(list(tags)),
            "family_friendly": cat_plan.get("family_friendly", True),
            "best_time": cat_plan.get("best_time", "all_day"),
            "tags": sorted(list(tags)),
        }

        scored_places.append(item)

    print(f"[Stage 12/20] Quality, field confidence, and anomaly scoring complete. Demoted {demoted_core_count} unverified places from core.")
    return scored_places
