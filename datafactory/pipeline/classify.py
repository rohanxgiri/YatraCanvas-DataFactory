import re
from typing import Dict, Any, List, Tuple
from collections import defaultdict
from ..config.settings import get_settings


# Name-token fallback rules (Weight 0.5 - used ONLY when structured sources are absent or inconclusive)
NAME_HEURISTICS = [
    # Lodging / Hospitality guards (Higher priority to avoid misclassifying hotels as palaces/monuments)
    (re.compile(r"(?i)\b(hotel|resort|palace hotel|residency|guest house|inn|homestay|dharamshala|bhavan)\b"), "hotel", "hotel", "support", 3.0),
    (re.compile(r"(?i)\b(oyo|treebo|fabhotel)\b"), "hotel", "hotel", "support", 3.5),
    # Transit guards (avoid misclassifying metro stations like Mansarovar as lakes)
    (re.compile(r"(?i)\b(railway station|metro station|junction|airport|bus stand|bus terminal|bus stop)\b"), "transport", "station", "support", 3.5),
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
    (re.compile(r"(?i)\b(bazaar|market|emporium|handicrafts)\b"), "shopping", "bazaar", "recommended", 0.5),
]


def vote_category(
    candidate: Dict[str, Any],
    source_mappings: Dict[str, Any]
) -> Tuple[str, str, float, List[Dict[str, Any]]]:
    """
    Implements multi-source Category Voting.
    Weights:
      - Wikidata entity type / subclass: 4.0
      - OSM travel tags (historic, tourism, amenity, leisure): 3.5
      - Wikivoyage listing type (see, do, eat, sleep, go): 3.0
      - Overture taxonomy: 2.0
      - Foursquare category: 2.0
      - Name heuristics: 0.5 (fallback only)
    Returns (winning_category, winning_subcategory, category_confidence, votes_list).
    """
    overture_map = source_mappings.get("overture", {})
    osm_map = source_mappings.get("osm", {})

    votes: Dict[Tuple[str, str], float] = defaultdict(float)
    votes_list: List[Dict[str, Any]] = []

    src = candidate.get("source")
    name = candidate.get("name", "")
    name_lower = name.lower()

    # 1. Wikidata Signal (Weight: 4.0)
    if src == "wikidata" or candidate.get("wikidata_id"):
        cat = candidate.get("category")
        subcat = candidate.get("subcategory")
        if cat and cat not in ("unknown", "experience"):
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
            weight = 2.0
            votes[(ov_cat, ov_subcat or "general")] += weight
            votes_list.append({"category": ov_cat, "subcategory": ov_subcat, "source": "overture", "weight": weight})
            break

    # 5. Name Heuristics (Weight 0.5 - or higher for explicit hotel/transit negative guards)
    matched_heuristic = False
    for pattern, h_cat, h_subcat, _, h_weight in NAME_HEURISTICS:
        if pattern.search(name):
            # If name is "Lake Palace", the palace rule matches with "palace" and "lake" matches "nature".
            # If both palace and lake are present, palace wins!
            if "palace" in name_lower and h_cat == "nature":
                continue
            if "station" in name_lower and h_cat == "nature":
                continue

            votes[(h_cat, h_subcat)] += h_weight
            votes_list.append({"category": h_cat, "subcategory": h_subcat, "source": "name_heuristic", "weight": h_weight})
            matched_heuristic = True
            break

    # Decide winner
    if votes:
        best_pair = max(votes.items(), key=lambda x: x[1])
        winning_cat, winning_subcat = best_pair[0]
        total_weight = sum(votes.values())
        winning_weight = best_pair[1]
        confidence = round(min(1.0, winning_weight / max(total_weight, 4.0)), 2)
        # If supported by structured sources, confidence is high
        if any(v["source"] in ("wikidata", "openstreetmap") for v in votes_list):
            confidence = max(0.85, confidence)
        elif any(v["source"] in ("wikivoyage", "overture") for v in votes_list):
            confidence = max(0.70, confidence)
        else:
            confidence = min(0.50, confidence)
        return winning_cat, winning_subcat, confidence, votes_list

    return "experience", "general_poi", 0.20, []


def run_classify(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Classifies normalized candidates into canonical YatraCanvas categories, subcategories,
    and initial place tier assignments using multi-source Category Voting.
    """
    settings = get_settings()
    cat_cfg = settings.categories_config
    source_mappings = cat_cfg.get("source_mappings", {})

    classified = []

    for c in candidates:
        item = dict(c)
        cat, subcat, cat_conf, votes = vote_category(item, source_mappings)

        item["category"] = cat
        item["subcategory"] = subcat
        item["category_confidence"] = cat_conf
        item["category_votes"] = votes

        # Attach default tags for canonical category and subcategory
        canonical_cats = cat_cfg.get("canonical_categories", {})
        default_tags = canonical_cats.get(cat, {}).get("default_tags", []) if cat else []
        current_tags = item.get("tags")
        tag_elements = [cat, subcat] + default_tags
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
        if any(w in name_lower for w in ["hotel", "oyo", "residency", "inn", "guest house", "marriage garden", "colony", "station", "junction"]):
            if suggested_tier == "core_destination":
                suggested_tier = "support" if cat in ("hotel", "transport") else "recommended"

        item["suggested_tier"] = suggested_tier
        classified.append(item)

    print(f"[Stage 8/20] Multi-source Category Voting complete across {len(classified)} places.")
    return classified
