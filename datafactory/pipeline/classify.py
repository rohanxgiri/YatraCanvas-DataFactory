import re
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict
from ..config.settings import get_settings


# Name-token fallback rules (Weight 0.5 - used ONLY when structured sources are absent or inconclusive)
NAME_HEURISTICS = [
    # Lodging / Hospitality guards (Higher priority to avoid misclassifying hotels as palaces/monuments)
    (re.compile(r"(?i)\b(hotel|resort|palace hotel|residency|guest house|guesthouse|inn|homestay|dharamshala|bhavan|hostel|motel)\b"), "hotel", "hotel", "support", 4.0),
    (re.compile(r"(?i)\b(oyo|treebo|fabhotel)\b"), "hotel", "hotel", "support", 4.0),
    # Transit guards (avoid misclassifying metro stations like Mansarovar as lakes; require structured evidence)
    (re.compile(r"(?i)\b(railway station|metro station|bus stand|bus terminal|bus stop)\b"), "transport", "station", "support", 1.5),
    # Core Heritage Structures
    (re.compile(r"(?i)\b(fort|garh|qila)\b"), "heritage", "fort", "core_destination", 0.5),
    (re.compile(r"(?i)\b(palace|mahal|haveli)\b"), "heritage", "palace", "core_destination", 0.5),
    (re.compile(r"(?i)\b(stepwell|baori|step well|kund)\b"), "heritage", "stepwell", "core_destination", 0.5),
    (re.compile(r"(?i)\b(ghat)\b"), "heritage", "ghat", "core_destination", 0.5),
    (re.compile(r"(?i)\b(monument|memorial|chhatri|cenotaph|stupa|pillar|tower)\b"), "heritage", "historical_monument", "core_destination", 0.5),
    (re.compile(r"(?i)\b(gate|darwaza|pole)\b"), "heritage", "gate", "core_destination", 0.5),
    (re.compile(r"(?i)\b(museum|art gallery|gallery|sangrahalaya)\b"), "museum", "history_museum", "core_destination", 0.5),
    (re.compile(r"(?i)\b(observatory|jantar mantar)\b"), "heritage", "observatory", "core_destination", 0.5),
    # Religious
    (re.compile(r"(?i)\b(temple|mandir|dewal|dham)\b"), "religious", "hindu_temple", "recommended", 0.5),
    (re.compile(r"(?i)\b(mosque|masjid|dargah|idgah)\b"), "religious", "mosque", "recommended", 0.5),
    (re.compile(r"(?i)\b(church|cathedral|chapel)\b"), "religious", "church", "recommended", 0.5),
    (re.compile(r"(?i)\b(gurudwara|gurdwara)\b"), "religious", "gurudwara", "recommended", 0.5),
    (re.compile(r"(?i)\b(jain mandir|derasar)\b"), "religious", "jain_temple", "recommended", 0.5),
    # Nature & Parks
    (re.compile(r"(?i)\b(lake|sarovar|talab|dam|waterfall)\b"), "nature", "lake", "recommended", 0.5),
    (re.compile(r"(?i)\b(garden|bagh|udyan|park)\b"), "park", "garden", "recommended", 0.5),
    (re.compile(r"(?i)\b(viewpoint|sunset point|sunrise point)\b"), "viewpoint", "scenic_viewpoint", "recommended", 0.5),
    # Food & Nightlife
    (re.compile(r"(?i)\b(cafe|coffee|roastery)\b"), "cafe", "coffee_shop", "discovery", 0.5),
    (re.compile(r"(?i)\b(restaurant|bhojanalaya|dhaba|dining|kitchen)\b"), "food", "restaurant", "discovery", 0.5),
    # Commercial retail / shops
    (re.compile(r"(?i)\b(bazaar|market|emporium|handicrafts)\b"), "shopping", "bazaar", "recommended", 0.5),
    (re.compile(r"(?i)\b(store|shop|stationery|tailor|jeweller|footwear|hardware|medical|pharmacy|mart|supermarket)\b"), "shopping", "shop", "support", 0.5),
]

LODGING_KEYWORDS = [
    "hotel", "resort", "inn", "guest house", "guesthouse", "oyo", "treebo",
    "fabhotel", "dharamshala", "homestay", "bhavan", "hostel", "motel",
    "palace hotel", "heritage hotel", "collection o", "capital o",
]

RESTAURANT_KEYWORDS = [
    "restaurant", "bhojanalaya", "dhaba", "dining", "kitchen", "sweets",
    "fast food", "food court", "bakery",
]

SHOP_KEYWORDS = [
    "store", "shop", "stationery", "tailor", "footwear", "jeweller",
    "hardware", "medical", "pharmacy", "mart", "supermarket", "provisions",
    "optical", "tailors", "textiles", "garments", "jewellers", "enterprises",
]


def has_structured_transport_evidence(candidate: Dict[str, Any]) -> bool:
    """
    Check if candidate has explicit structured transport tags from OSM, Wikidata, or Overture.
    Name/address tokens alone are strictly insufficient.
    """
    raw_tags = candidate.get("tags")
    tags = raw_tags if isinstance(raw_tags, dict) else {}
    if tags.get("railway") in ("station", "halt", "subway_entrance"):
        return True
    if tags.get("public_transport") in ("station", "stop_position"):
        return True
    if tags.get("amenity") in ("bus_station", "ferry_terminal"):
        return True
    if tags.get("aeroway") in ("aerodrome", "terminal"):
        return True
    if candidate.get("listing_type") == "go":
        return True

    # Overture transport taxonomy hints
    for hint in candidate.get("category_hints", []):
        if not hint:
            continue
        clean_hint = hint.lower().strip().replace(" ", "_")
        if clean_hint in (
            "train_station", "bus_station", "airport", "public_transport",
            "transportation", "railway_station", "subway_station", "metro_station"
        ):
            return True

    # Wikidata transport class
    if (candidate.get("source") == "wikidata" or candidate.get("wikidata_id")) and candidate.get("category") == "transport":
        return True

    return False


def determine_primary_entity_type(
    category: str,
    subcategory: Optional[str] = None,
    tags: Optional[List[str]] = None,
    name: str = ""
) -> str:
    """
    Assigns a single canonical primary_entity_type from the standardized taxonomy.
    """
    cat = (category or "").lower().strip()
    subcat = (subcategory or "").lower().strip()
    name_lower = name.lower()

    if cat == "hotel":
        return "hotel"
    elif cat == "cafe":
        return "cafe"
    elif cat == "food":
        return "restaurant"
    elif cat == "museum":
        return "museum"
    elif cat == "religious":
        return "religious_site"
    elif cat == "viewpoint":
        return "viewpoint"
    elif cat == "transport":
        # Require structured subcategory evidence, not loose name tokens
        if any(w in subcat for w in ["airport", "aerodrome"]):
            return "airport"
        elif any(w in subcat for w in ["bus", "bus_station"]):
            return "bus_station"
        elif any(w in subcat for w in ["railway", "train", "metro", "station"]):
            return "railway_station"
        return "transport_hub"

    elif cat == "heritage":
        if "fort" in subcat or any(w in name_lower for w in ["fort", "garh", "qila"]):
            return "fort"
        elif "palace" in subcat or any(w in name_lower for w in ["palace", "mahal"]):
            return "palace"
        elif any(w in subcat or w in name_lower for w in ["monument", "memorial", "chhatri", "cenotaph", "stupa", "stepwell", "baori"]):
            return "monument"
        elif "ghat" in subcat or "ghat" in name_lower:
            return "historic_site"
        elif "observatory" in subcat or "observatory" in name_lower:
            return "tourist_attraction"
        return "historic_site"
    elif cat == "park":
        if "garden" in subcat or any(w in name_lower for w in ["garden", "bagh", "udyan"]):
            return "garden"
        return "park"
    elif cat == "nature":
        if "lake" in subcat or any(w in name_lower for w in ["lake", "sarovar", "talab", "dam"]):
            return "lake"
        return "tourist_attraction"
    elif cat == "shopping":
        if any(w in subcat or w in name_lower for w in ["market", "bazaar", "mandi"]):
            return "market"
        return "shop"
    elif cat == "arts_culture":
        return "arts_venue"
    elif cat == "experience":
        return "experience"

    return "other"


def vote_category(
    candidate: Dict[str, Any],
    source_mappings: Dict[str, Any]
) -> Tuple[str, str, float, List[Dict[str, Any]]]:
    """
    Implements multi-source Category Voting with strict negative category guards.
    Weights:
      - Wikidata entity type / subclass: 4.0
      - OSM travel tags (historic, tourism, amenity, leisure): 3.5
      - Wikivoyage listing type (see, do, eat, sleep, go): 3.0
      - Overture taxonomy: 2.0
      - Foursquare category: 2.0
      - Name heuristics: 0.5 (fallback only)
    Returns (winning_category, winning_subcategory, category_confidence, votes_list, secondary_tags).
    """
    overture_map = source_mappings.get("overture", {})
    osm_map = source_mappings.get("osm", {})

    votes: Dict[Tuple[str, str], float] = defaultdict(float)
    votes_list: List[Dict[str, Any]] = []
    secondary_tags: List[str] = []

    src = candidate.get("source")
    name = candidate.get("name", "")
    name_lower = name.lower()

    # Pre-detect strong negative signals
    is_lodging_name = any(re.search(r"\b" + re.escape(k) + r"\b", name_lower) for k in LODGING_KEYWORDS)
    is_restaurant_name = any(re.search(r"\b" + re.escape(k) + r"\b", name_lower) for k in RESTAURANT_KEYWORDS)
    is_shop_name = any(re.search(r"\b" + re.escape(k) + r"\b", name_lower) for k in SHOP_KEYWORDS)

    # 1. Wikidata Signal (Weight: 4.0)
    if src == "wikidata" or candidate.get("wikidata_id"):
        cat = candidate.get("category")
        subcat = candidate.get("subcategory")
        if cat and cat not in ("unknown", "experience"):
            # Guard: If Wikidata says park/heritage but entity name is clearly a hotel/OYO, re-route to hotel!
            if is_lodging_name and cat in ("park", "heritage", "nature", "cafe"):
                cat = "hotel"
                subcat = "hotel"
            weight = 4.0
            votes[(cat, subcat or "general")] += weight
            votes_list.append({"category": cat, "subcategory": subcat, "source": "wikidata", "weight": weight})

    # 2. OSM Travel Tags (Weight: 3.5)
    raw_tags = candidate.get("tags")
    tags = raw_tags if isinstance(raw_tags, dict) else {}
    osm_cat, osm_subcat = None, None
    for key in ["historic", "tourism", "amenity", "leisure", "natural", "railway", "aeroway"]:
        val = tags.get(key)
        if val and key in osm_map and val in osm_map[key]:
            mapping = osm_map[key][val]
            osm_cat = mapping.get("category")
            osm_subcat = mapping.get("subcategory")
            if osm_cat == "religious" and "religion" in tags:
                rel = tags.get("religion", "").lower()
                rel_map = {
                    "hindu": "hindu_temple",
                    "muslim": "mosque",
                    "christian": "church",
                    "sikh": "gurudwara",
                    "jain": "jain_temple",
                    "buddhist": "buddhist_temple",
                }
                if rel in rel_map:
                    osm_subcat = rel_map[rel]
            # Guard against lodging misclassification
            if is_lodging_name and osm_cat in ("park", "heritage", "nature", "cafe"):
                osm_cat = "hotel"
                osm_subcat = "hotel"
            weight = 3.5
            votes[(osm_cat, osm_subcat or "general")] += weight
            votes_list.append({"category": osm_cat, "subcategory": osm_subcat, "source": "openstreetmap", "weight": weight})
            break

    # 3. Wikivoyage Listing Type (Weight: 3.0)
    listing_type = candidate.get("listing_type")
    if listing_type:
        wv_map = {
            "see": ("heritage", "attraction"),
            "do": ("experience", "activity"),
            "eat": ("food", "restaurant"),
            "drink": ("cafe", "coffee_shop"),
            "buy": ("shopping", "bazaar"),
            "sleep": ("hotel", "hotel"),
            "go": ("transport", "station"),
        }
        if listing_type in wv_map:
            wv_cat, wv_subcat = wv_map[listing_type]
            # Guard: If Wikivoyage listing is "drink" or "eat" but place is clearly a Hotel (e.g. Radisson Hotel Varanasi),
            # the primary category must be hotel, and secondary tags store the dining/cafe amenity!
            if is_lodging_name and wv_cat in ("cafe", "food"):
                secondary_tags.extend([wv_cat, wv_subcat, "bar" if listing_type == "drink" else "dining"])
                wv_cat = "hotel"
                wv_subcat = "hotel"
            weight = 3.0
            votes[(wv_cat, wv_subcat)] += weight
            votes_list.append({"category": wv_cat, "subcategory": wv_subcat, "source": "wikivoyage", "weight": weight})

    # 4. Overture Taxonomy (Weight: 2.0)
    for hint in candidate.get("category_hints", []):
        if not hint:
            continue
        clean_hint = hint.lower().strip().replace(" ", "_")
        if clean_hint in overture_map:
            mapping = overture_map[clean_hint]
            ov_cat = mapping.get("category")
            ov_subcat = mapping.get("subcategory")
            if is_lodging_name and ov_cat in ("park", "heritage", "nature", "cafe"):
                ov_cat = "hotel"
                ov_subcat = "hotel"
            weight = 2.0
            votes[(ov_cat, ov_subcat or "general")] += weight
            votes_list.append({"category": ov_cat, "subcategory": ov_subcat, "source": "overture", "weight": weight})
            break

    # 5. Name Heuristics (Weight 0.5 - or higher for explicit hotel/transit negative guards)
    for pattern, h_cat, h_subcat, _, h_weight in NAME_HEURISTICS:
        if pattern.search(name):
            if is_lodging_name and h_cat in ("park", "nature", "cafe", "heritage", "transport"):
                continue
            if is_restaurant_name and h_cat in ("heritage", "transport"):
                continue
            if is_shop_name and h_cat in ("heritage", "transport", "park", "nature"):
                continue
            if "palace" in name_lower and h_cat == "nature":
                continue
            if "station" in name_lower and h_cat == "nature":
                continue

            # Strict transit hardening: Name/address tokens alone ("Station Road", "Junction", etc.)
            # must NOT create transport entities without structured evidence!
            if h_cat == "transport":
                is_address_road = bool(re.search(r"(?i)\b(road|marg|street|lane|nagar|colony|opp|near|behind|chowk)\b", name_lower))
                if is_address_road or not has_structured_transport_evidence(candidate):
                    continue

            votes[(h_cat, h_subcat)] += h_weight
            votes_list.append({"category": h_cat, "subcategory": h_subcat, "source": "name_heuristic", "weight": h_weight})
            break

    # 6. Apply Negative Category Guards to All Votes
    if is_lodging_name:
        # Purge any park, nature, or cafe votes completely
        votes = {k: v for k, v in votes.items() if k[0] not in ("park", "nature", "cafe")}
        # If it has "Palace" in name but is clearly an OYO / Hotel (not verified heritage), purge heritage
        if not any(v.get("source") == "wikidata" and candidate.get("heritage") for v in votes_list):
            votes = {k: v for k, v in votes.items() if k[0] != "heritage"}
        votes[("hotel", "hotel")] = max(votes.get(("hotel", "hotel"), 0.0), 4.5)

    if is_restaurant_name:
        votes = {k: v for k, v in votes.items() if k[0] != "heritage"}
        votes[("food", "restaurant")] = max(votes.get(("food", "restaurant"), 0.0), 3.5)

    # Purge transport votes for shops/restaurants/hotels that lack structured transport evidence
    if is_shop_name or is_restaurant_name or is_lodging_name:
        if not has_structured_transport_evidence(candidate):
            votes = {k: v for k, v in votes.items() if k[0] != "transport"}


    # 7. Decide Winner
    if votes:
        best_pair = max(votes.items(), key=lambda x: x[1])
        winning_cat, winning_subcat = best_pair[0]
        total_weight = sum(votes.values())
        winning_weight = best_pair[1]
        confidence = round(min(1.0, winning_weight / max(total_weight, 4.0)), 2)
        if any(v["source"] in ("wikidata", "openstreetmap") for v in votes_list):
            confidence = max(0.85, confidence)
        elif any(v["source"] in ("wikivoyage", "overture") for v in votes_list):
            confidence = max(0.70, confidence)
        else:
            confidence = min(0.50, confidence)
        candidate["secondary_tags"] = secondary_tags
        return winning_cat, winning_subcat, confidence, votes_list

    # Fallback: If it has shop keywords (e.g. A.L store Udaipur, stationery), classify as shopping/shop, NOT experience!
    if is_shop_name:
        candidate["secondary_tags"] = []
        return "shopping", "shop", 0.40, [{"category": "shopping", "subcategory": "shop", "source": "shop_guard", "weight": 2.0}]

    candidate["secondary_tags"] = []
    return "experience", "general_poi", 0.20, []


def run_classify(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Classifies normalized candidates into canonical YatraCanvas categories, subcategories,
    primary entity types, and initial place tier assignments using multi-source Category Voting.
    """
    settings = get_settings()
    cat_cfg = settings.categories_config
    source_mappings = cat_cfg.get("source_mappings", {})

    classified = []

    for c in candidates:
        item = dict(c)
        cat, subcat, cat_conf, votes = vote_category(item, source_mappings)
        sec_tags = item.get("secondary_tags", [])

        item["category"] = cat
        item["subcategory"] = subcat
        item["category_confidence"] = cat_conf
        item["category_votes"] = votes

        # Assign canonical primary_entity_type
        primary_entity_type = determine_primary_entity_type(
            category=cat,
            subcategory=subcat,
            tags=item.get("tags", []),
            name=item.get("name", "")
        )
        item["primary_entity_type"] = primary_entity_type

        # Attach default tags for canonical category and subcategory plus secondary tags
        canonical_cats = cat_cfg.get("canonical_categories", {})
        default_tags = canonical_cats.get(cat, {}).get("default_tags", []) if cat else []
        current_tags = item.get("tags") or []
        tag_elements = [cat, subcat, primary_entity_type] + default_tags + sec_tags
        if isinstance(current_tags, list):
            tag_elements = current_tags + tag_elements
        item["tags"] = [t for t in dict.fromkeys(tag_elements) if t]

        # Determine suggested initial tier
        suggested_tier = item.get("suggested_tier")
        if not suggested_tier:
            if cat in ("hotel", "transport"):
                suggested_tier = "support"
            elif cat in ("heritage", "museum"):
                suggested_tier = "core_destination"
            elif cat in ("religious", "park", "nature", "viewpoint"):
                suggested_tier = "recommended"
            elif cat in ("food", "cafe", "shopping"):
                suggested_tier = "recommended"
            else:
                suggested_tier = "discovery"

        # Demote generic commercial names from ever becoming core_destination
        name_lower = item.get("name", "").lower()
        if any(w in name_lower for w in ["hotel", "oyo", "residency", "inn", "guest house", "marriage garden", "colony", "station", "junction", "store", "shop"]):
            if suggested_tier == "core_destination":
                suggested_tier = "support" if cat in ("hotel", "transport") else "recommended"

        item["suggested_tier"] = suggested_tier
        classified.append(item)

    print(f"[Stage 8/20] Multi-source Category Voting & Primary Entity Classification complete across {len(classified)} places.")
    return classified
