import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..utils.text import normalize_name, clean_string


QUERY_INTENT_MAP: Dict[str, Dict[str, Any]] = {
    "cafe": {
        "categories": ["cafe"],
        "entity_types": ["cafe"],
        "subcategories": ["coffee_shop", "bakery", "cafe"],
    },
    "coffee": {
        "categories": ["cafe"],
        "entity_types": ["cafe"],
        "subcategories": ["coffee_shop", "cafe"],
    },
    "coffee shop": {
        "categories": ["cafe"],
        "entity_types": ["cafe"],
        "subcategories": ["coffee_shop", "cafe"],
    },
    "restaurant": {
        "categories": ["food"],
        "entity_types": ["restaurant"],
        "subcategories": ["restaurant", "dining"],
    },
    "food": {
        "categories": ["food", "cafe"],
        "entity_types": ["restaurant", "cafe"],
        "subcategories": ["restaurant", "dhaba", "bhojanalaya", "dining", "fast_food", "food_court", "street_food", "bakery", "coffee_shop"],
    },
    "fort": {
        "categories": ["heritage"],
        "entity_types": ["fort"],
        "subcategories": ["fort"],
    },
    "palace": {
        "categories": ["heritage"],
        "entity_types": ["palace"],
        "subcategories": ["palace"],
    },
    "heritage": {
        "categories": ["heritage", "museum"],
        "entity_types": ["historic_site", "fort", "palace", "monument", "tourist_attraction", "museum"],
        "subcategories": ["attraction", "fort", "palace", "historical_monument", "monument", "ghat", "stepwell", "history_museum", "observatory"],
    },
    "museum": {
        "categories": ["museum"],
        "entity_types": ["museum"],
        "subcategories": ["history_museum", "art_museum", "science_museum", "museum"],
    },
    "park": {
        "categories": ["park"],
        "entity_types": ["park", "garden"],
        "subcategories": ["park", "garden", "city_park"],
    },
    "garden": {
        "categories": ["park"],
        "entity_types": ["garden", "park"],
        "subcategories": ["garden", "botanical_garden"],
    },
    "lake": {
        "categories": ["nature"],
        "entity_types": ["lake", "tourist_attraction"],
        "subcategories": ["lake", "waterbody"],
    },
    "market": {
        "categories": ["shopping"],
        "entity_types": ["market", "shop"],
        "subcategories": ["market", "bazaar", "mandi"],
    },
    "shopping": {
        "categories": ["shopping"],
        "entity_types": ["market", "shop"],
        "subcategories": ["shopping", "bazaar", "market", "emporium", "handicrafts", "mall", "shop"],
    },
    "temple": {
        "categories": ["religious"],
        "entity_types": ["religious_site"],
        "subcategories": ["hindu_temple", "jain_temple", "buddhist_temple", "temple", "place_of_worship"],
    },
    "mosque": {
        "categories": ["religious"],
        "entity_types": ["religious_site"],
        "subcategories": ["mosque", "dargah", "idgah", "place_of_worship"],
    },
    "hotel": {
        "categories": ["hotel"],
        "entity_types": ["hotel"],
        "subcategories": ["hotel", "resort", "guest_house", "homestay"],
    },
    "railway station": {
        "categories": ["transport"],
        "entity_types": ["railway_station"],
        "subcategories": ["station", "railway_station", "train_station"],
    },
    "art": {
        "categories": ["arts_culture", "museum"],
        "entity_types": ["arts_venue", "museum"],
        "subcategories": ["art_gallery", "gallery", "art_museum", "arts_centre"],
    },
}


def is_eligible_for_discovery(p: Dict[str, Any]) -> bool:
    """
    Computes whether a place record is eligible for Discovery / Hidden Gem candidate scoring.
    Requires:
      - Valid coordinates and not quarantined
      - Identity and category confidence above threshold
      - Travel relevance >= 0.35
      - Not support tier / infrastructure
      - Not lodging/hotel (e.g. OYO, Hotel Parmanand Garden, Collection O)
      - Not generic commercial retail/shop (e.g. A.L store Udaipur, stationery shops)
      - Not corporate/commercial services or administrative features
      - Belongs to approved travel categories
    """
    c_info = p.get("classification", {})
    cat = (c_info.get("category") or p.get("category", "")).lower().strip()
    subcat = (c_info.get("subcategory") or p.get("subcategory", "")).lower().strip()
    primary_entity = (c_info.get("primary_entity_type") or p.get("primary_entity_type", "")).lower().strip()
    tier = (p.get("tier") or "").lower().strip()
    name = (p.get("name", "")).lower().strip()

    # 1. Quarantined or anomaly
    if p.get("anomaly_score", 0.0) > 0.40 or p.get("anomaly_flags"):
        return False

    # 2. Coordinates
    loc = p.get("location", {})
    lat = loc.get("latitude") or p.get("latitude")
    lon = loc.get("longitude") or p.get("longitude")
    if lat is None or lon is None or (lat == 0.0 and lon == 0.0):
        return False

    # 3. Confidence thresholds
    qual = p.get("quality") or {}
    fc = qual.get("field_confidence") or {}
    id_conf = float(fc.get("identity_confidence", qual.get("identity_confidence", 0.7)))
    cat_conf = float(fc.get("category_confidence", p.get("category_confidence", 0.7)))
    t_rel = float(p.get("travel_relevance_score", 0.5) or 0.5)

    if id_conf < 0.50 or cat_conf < 0.40:
        return False

    # 3b. Tier check: must be discovery or recommended
    if tier not in ("discovery", "recommended"):
        return False

    # 4. Exclude lodging & accommodation
    if cat == "hotel" or primary_entity == "hotel":
        return False
    if any(re.search(r"\b" + re.escape(w) + r"\b", name) for w in ["hotel", "oyo", "resort", "inn", "guest house", "guesthouse", "homestay", "dharamshala", "hostel", "motel", "collection o", "capital o"]):
        return False

    # 5. Exclude transport / infrastructure
    if cat in ("transport", "airport", "railway_station", "bus_station", "station") or primary_entity in ("railway_station", "airport", "bus_station"):
        return False

    # 6. Exclude generic commercial retail / stores / civic & professional services
    if primary_entity in ("shop", "service", "office"):
        return False
    if any(re.search(r"\b" + re.escape(w) + r"\b", name) for w in [
        "store", "stationery", "tailor", "jeweller", "hardware", "medical",
        "pharmacy", "repair", "clinic", "hospital", "dispensary", "nursing home",
        "enterprise", "footwear", "provisions", "optical", "bank", "atm",
        "branch", "post office", "police station", "school", "college"
    ]):
        return False

    # 7. Exclude administrative boundaries
    if any(w in name for w in ["district", "tehsil", "ward no", "gram panchayat", "circle"]):
        return False

    # 8. Permitted categories
    ALLOWED_DISCOVERY_CATEGORIES = {
        "heritage", "religious", "museum", "park", "garden", "nature",
        "viewpoint", "arts_culture", "market", "experience", "cafe", "food", "shopping"
    }
    if cat not in ALLOWED_DISCOVERY_CATEGORIES:
        return False

    if cat == "food" and t_rel < 0.50:
        return False

    if cat == "shopping" and subcat not in ("bazaar", "market", "handicrafts", "emporium"):
        return False

    return True


def compute_discovery_score(p: Dict[str, Any]) -> float:
    """
    Calculates the YatraCanvas Discovery / Hidden Gem candidate heuristic score.
    Heuristic only; this does NOT represent real-world popularity data.
    Returns 0.0 if the record is ineligible.
    """
    if not is_eligible_for_discovery(p):
        return 0.0

    quality_dict = p.get("quality")
    if isinstance(quality_dict, dict) and quality_dict.get("overall") is not None:
        q_val = float(quality_dict["overall"])
    elif p.get("quality_overall") is not None:
        q_val = float(p["quality_overall"])
    else:
        q_val = 0.6

    t_rel = float(p.get("travel_relevance_score", 0.5) or 0.5)
    prom = float(p.get("prominence_score", 0.5) or 0.5)

    score = (t_rel * 0.40) + (q_val * 0.40) + ((1.0 - min(1.0, max(0.0, prom))) * 0.20)
    return round(score, 3)


class CityPackSearchEngine:
    """
    Standalone category-first search engine for testing City Pack offline datasets.
    Implements query intent normalization, category-first ranking, no artificial
    padding on sparse queries, and full score explainability.
    """

    def __init__(self, city_name: str, version: str = "v3", project_root: Optional[Path] = None):
        if project_root is None:
            project_root = Path(__file__).resolve().parent.parent.parent

        self.city_name = city_name
        self.version = version
        self.project_root = project_root
        self.places: List[Dict[str, Any]] = []
        self._load_places()

    def _load_places(self) -> None:
        releases_dir = self.project_root / "releases"
        matched_file: Optional[Path] = None

        for p_json in releases_dir.glob(f"**/{self.version}/places.json"):
            parts = [part.lower() for part in p_json.parts]
            if self.city_name.lower() in parts:
                matched_file = p_json
                break

        if not matched_file:
            for p_json in releases_dir.glob("**/places.json"):
                parts = [part.lower() for part in p_json.parts]
                if self.city_name.lower() in parts:
                    matched_file = p_json
                    break

        if matched_file and matched_file.exists():
            with open(matched_file, "r", encoding="utf-8") as f:
                self.places = json.load(f)
        else:
            self.places = []

    def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        tier: Optional[str] = None,
        limit: int = 20,
        min_quality: float = 0.0,
        discovery_mode: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Executes search with category-first ranking, intent normalization,
        and score explainability.
        """
        if not self.places:
            return []

        raw_query = (query or "").strip().lower()
        q_norm = normalize_name(raw_query).lower() if raw_query else ""
        q_tokens = [w for w in q_norm.split() if len(w) > 1] if q_norm else []

        cat_filter = category.lower().strip() if category else None
        subcat_filter = subcategory.lower().strip() if subcategory else None
        tier_filter = tier.lower().strip() if tier else None

        # Resolve Query Intent
        intent_info = QUERY_INTENT_MAP.get(raw_query) or QUERY_INTENT_MAP.get(q_norm)
        has_category_intent = intent_info is not None or cat_filter is not None

        results = []

        for p in self.places:
            c_info = p.get("classification", {})
            p_cat = (c_info.get("category") or p.get("category") or "").lower()
            p_subcat = (c_info.get("subcategory") or p.get("subcategory") or "").lower()
            p_entity_type = (c_info.get("primary_entity_type") or p.get("primary_entity_type") or "").lower()
            p_tier = (p.get("tier") or "").lower()

            # Exact filters
            if cat_filter and p_cat != cat_filter:
                continue
            if subcat_filter and p_subcat != subcat_filter:
                continue
            if tier_filter and p_tier != tier_filter:
                continue

            quality_val = float(p.get("quality", {}).get("overall", 0.0) if isinstance(p.get("quality"), dict) else p.get("quality_overall", 0.0))
            if quality_val < min_quality:
                continue

            disc_score = compute_discovery_score(p)

            # Scoring and Explainability
            match_score = 0.0
            matched_fields: List[str] = []
            category_matched = False
            name_matched = False
            tag_matched = False

            p_name = p.get("name", "")
            p_name_norm = normalize_name(p_name).lower()
            p_name_hi = p.get("name_hi") or ""
            p_alts = p.get("alternate_names") or []
            p_tags = [t.lower() for t in c_info.get("tags", [])]
            p_addr = (p.get("location", {}).get("address") or "").lower()
            p_prose = ""
            if isinstance(p.get("prose"), dict):
                p_prose = p.get("prose", {}).get("text", "").lower()

            if q_norm:
                # -------------------------------------------------------------
                # 1. Intent / Category Match (Category-First Ranking)
                # -------------------------------------------------------------
                if intent_info:
                    target_cats = intent_info.get("categories", [])
                    target_entities = intent_info.get("entity_types", [])
                    target_subcats = intent_info.get("subcategories", [])

                    if p_entity_type in target_entities:
                        match_score += 220.0
                        category_matched = True
                        matched_fields.append(f"entity_type:{p_entity_type}")
                    elif p_cat in target_cats:
                        match_score += 180.0
                        category_matched = True
                        matched_fields.append(f"category:{p_cat}")

                    if p_subcat in target_subcats:
                        match_score += 120.0
                        category_matched = True
                        matched_fields.append(f"subcategory:{p_subcat}")

                # Direct category query match
                if not category_matched:
                    if q_norm == p_cat or q_norm in p_cat:
                        match_score += 160.0
                        category_matched = True
                        matched_fields.append(f"category:{p_cat}")
                    elif q_norm == p_subcat or q_norm in p_subcat:
                        match_score += 120.0
                        category_matched = True
                        matched_fields.append(f"subcategory:{p_subcat}")

                # -------------------------------------------------------------
                # 2. Canonical Name Matches
                # -------------------------------------------------------------
                if q_norm == p_name_norm:
                    match_score += 150.0
                    name_matched = True
                    matched_fields.append("name:exact")
                elif p_name_norm.startswith(q_norm + " ") or p_name_norm.endswith(" " + q_norm):
                    match_score += 100.0
                    name_matched = True
                    matched_fields.append("name:phrase")
                elif q_norm in p_name_norm:
                    match_score += 70.0
                    name_matched = True
                    matched_fields.append("name:contains")

                # -------------------------------------------------------------
                # 3. Multilingual / Alternate Names
                # -------------------------------------------------------------
                if query and (query in p_name_hi or q_norm in normalize_name(p_name_hi).lower()):
                    match_score += 120.0
                    name_matched = True
                    matched_fields.append("name_hi:exact")
                for alt in p_alts:
                    alt_norm = normalize_name(alt).lower()
                    if q_norm == alt_norm:
                        match_score += 110.0
                        name_matched = True
                        matched_fields.append("alternate_name:exact")
                        break
                    elif q_norm in alt_norm:
                        match_score += 60.0
                        name_matched = True
                        matched_fields.append("alternate_name:contains")
                        break

                # -------------------------------------------------------------
                # 4. Token Matches in Tags
                # -------------------------------------------------------------
                for tok in q_tokens:
                    if any(tok == t or tok in t for t in p_tags):
                        match_score += 30.0
                        tag_matched = True
                        matched_fields.append(f"tag:{tok}")

                # -------------------------------------------------------------
                # 5. Token Matches in Name
                # -------------------------------------------------------------
                for tok in q_tokens:
                    if tok in p_name_norm.split():
                        match_score += 40.0
                        name_matched = True
                        matched_fields.append(f"name_token:{tok}")

                # -------------------------------------------------------------
                # 6. Address / Description Matches (Never Dominates Intent)
                # -------------------------------------------------------------
                for tok in q_tokens:
                    if tok in p_addr.split():
                        # If query is category-intent (e.g. railway station) and place is NOT that category,
                        # do NOT reward address matching (e.g. Station Road hotel should NOT rank as railway station)
                        if has_category_intent and not category_matched:
                            continue
                        match_score += 5.0
                        matched_fields.append(f"address:{tok}")

                # -------------------------------------------------------------
                # Intent Filtering: Filter out irrelevant padding
                # -------------------------------------------------------------
                # If query was a dedicated category intent (e.g. railway station, mosque, cafe, hotel, fort),
                # do NOT return places that failed category match and only matched partial name/address tokens!
                if intent_info and not category_matched:
                    # Allow only if the full canonical name equals or explicitly contains the query phrase
                    if not (q_norm == p_name_norm or raw_query in p_name_norm):
                        continue
                    # Never allow hotels or shops to hijack other category queries
                    if p_cat in ("hotel", "shopping") and raw_query not in ("hotel", "shopping", "market"):
                        continue

                if match_score <= 0.0:
                    continue
            else:
                match_score = 10.0
                matched_fields.append("default")

            t_rel = float(p.get("travel_relevance_score", 0.0) or 0.0)
            prom = float(p.get("prominence_score", 0.0) or 0.0)

            total_rank = match_score + (t_rel * 25.0) + (prom * 15.0)
            if discovery_mode or (tier_filter == "discovery" and not query):
                total_rank = disc_score * 100.0 + match_score

            results.append({
                "id": p.get("id") or p.get("canonical_id"),
                "name": p_name,
                "name_hi": p_name_hi,
                "category": p_cat,
                "subcategory": p_subcat,
                "primary_entity_type": p_entity_type,
                "tier": p_tier,
                "latitude": p.get("location", {}).get("latitude") or p.get("latitude"),
                "longitude": p.get("location", {}).get("longitude") or p.get("longitude"),
                "address": p.get("location", {}).get("address"),
                "travel_relevance_score": t_rel,
                "prominence_score": prom,
                "quality_overall": quality_val,
                "discovery_score": disc_score,
                "has_image": bool(p.get("images", {}).get("primary") if isinstance(p.get("images"), dict) else p.get("primary_image_path")),
                "has_hours": bool(p.get("opening_hours")),
                "search_score": round(match_score, 1),
                "matched_fields": matched_fields,
                "intent_match": raw_query if intent_info else None,
                "category_match": category_matched,
                "name_match": name_matched,
                "tag_match": tag_matched,
                "total_rank": round(total_rank, 2),
            })

        if discovery_mode or (tier_filter == "discovery" and not query):
            results.sort(key=lambda x: (x["discovery_score"], x["quality_overall"]), reverse=True)
        else:
            results.sort(key=lambda x: x["total_rank"], reverse=True)

        return results[:limit]
