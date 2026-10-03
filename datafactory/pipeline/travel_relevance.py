import re
from typing import Dict, Any, List, Tuple, Set, Optional


# High-Confidence Non-Travel Amenity Tags in OSM
BLOCKED_OSM_AMENITIES = {
    "bank", "atm", "bureau_de_change", "money_transfer", "payment_terminal",
    "post_office", "police", "fire_station", "courthouse", "townhall", "prison",
    "fuel", "car_wash", "car_rental", "charging_station", "vehicle_inspection",
    "parking", "parking_space", "parking_entrance", "bicycle_parking", "motorcycle_parking",
    "vending_machine", "grit_bin", "recycling", "waste_disposal", "waste_basket", "toilets",
    "dentist", "pharmacy", "clinic", "doctors", "hospital", "nursing_home", "social_facility",
    "veterinary", "community_centre", "kindergarten", "school", "college", "university",
    "research_institute", "language_school", "music_school", "driving_school"
}

BLOCKED_OSM_OFFICES = {
    "financial", "insurance", "estate_agent", "company", "logistics", "courier",
    "tax_advisor", "lawyer", "accountant", "telecommunication", "government", "it",
    "consulting", "employment_agency", "association", "ngo", "newspaper", "yes",
    "commercial", "administrative", "advertising_agency"
}

BLOCKED_OSM_SHOPS = {
    "car", "car_repair", "car_parts", "motorcycle", "tyres", "hardware", "doityourself",
    "trade", "plumber", "glaziery", "chemist", "optician", "medical_supply",
    "hearing_aids", "laundry", "dry_cleaning", "estate_agent", "copier", "locksmith",
    "pawnbroker", "money_lender", "tailor", "hairdresser", "beauty", "cosmetics"
}

BLOCKED_OSM_BUILDINGS = {
    "apartments", "residential", "house", "detached", "terrace", "dormitory",
    "barracks", "industrial", "warehouse", "commercial", "office", "garage",
    "garages", "shed", "roof", "transformer_tower", "substation", "service"
}

CORE_TRAVEL_CATEGORIES = {
    "heritage", "museum", "viewpoint", "nature", "park", "arts_culture"
}

SECONDARY_TRAVEL_CATEGORIES = {
    "food", "cafe", "shopping", "hotel", "transport", "religious", "experience", "entertainment"
}


# Positive semantic POI amenity tags in OSM
POSITIVE_OSM_AMENITIES = {
    "restaurant", "cafe", "fast_food", "bar", "pub", "ice_cream", "food_court",
    "marketplace", "place_of_worship", "theatre", "cinema", "arts_centre"
}

# Overture Core Travel taxonomy
OVERTURE_TRAVEL_TAXONOMY = {
    "palace", "fort", "castle", "monument", "historic_site", "memorial",
    "museum", "art_gallery", "scenic_viewpoint", "botanical_garden", "zoo",
    "landmark_and_historical_building", "historical_landmark"
}

# Overture Secondary Travel taxonomy
OVERTURE_SECONDARY_TAXONOMY = {
    "restaurant", "cafe", "coffee_shop", "tea_room", "tea_house", "bakery",
    "sweet_shop", "confectionery", "non_alcoholic_beverage_venue", "shopping_mall",
    "market", "hotel", "resort", "hostel", "heritage_hotel", "bed_and_breakfast",
    "train_station", "airport", "bus_station", "hindu_temple", "mosque", "church",
    "place_of_worship", "gurudwara", "jain_temple", "arts_crafts_and_hobby_store",
    "arts_and_crafts", "handicraft", "art_and_craft_goods_store"
}


def prefilter_candidate(
    candidate: Dict[str, Any],
    cat_cfg: Dict[str, Any]
) -> Tuple[str, str, Dict[str, Any]]:
    """
    STAGE 1: Fast Relevance Prefilter.
    Evaluates candidate metadata before entity resolution.
    Returns:
      (relevance_stage, reason_code, evidence)
      where relevance_stage is:
        - "EXCLUDE": high-confidence non-travel junk
        - "TRAVEL_CANDIDATE": clear positive travel evidence
        - "SECONDARY_TRAVEL_CANDIDATE": secondary commercial category (food, cafe, hotel, shopping)
        - "REVIEW_CANDIDATE": ambiguous/unclassified place requiring entity resolution
    """
    rej_rules = cat_cfg.get("rejection_rules", {})
    blocked_categories = set(rej_rules.get("blocked_categories", []))
    blocked_hierarchies = set(rej_rules.get("blocked_hierarchies", []))
    blocked_patterns = [re.compile(p) for p in rej_rules.get("blocked_name_patterns", [])]
    whitelist_patterns = [re.compile(p) for p in rej_rules.get("whitelist_name_patterns", [])]

    name = candidate.get("name", "").strip()
    source = candidate.get("source", "")
    raw_tags = candidate.get("tags")
    tags = raw_tags if isinstance(raw_tags, dict) else {}
    cat_hints = candidate.get("category_hints") or []

    # 1. Whitelist Check (e.g. historic gates like Ajmeri Gate, Tripoliya Gate)
    for wp in whitelist_patterns:
        m = wp.search(name)
        if m:
            return "TRAVEL_CANDIDATE", "WHITELISTED_LANDMARK", {"pattern": m.group(0), "name": name}

    # 2. Hard OSM Tag Negatives (Amenity, Office, Shop, Industrial, Blocked Craft)
    osm_amenity = tags.get("amenity", "").lower()
    if osm_amenity in BLOCKED_OSM_AMENITIES:
        code = "NON_TRAVEL_FINANCIAL_SERVICE" if osm_amenity in ("bank", "atm", "bureau_de_change") else f"OSM_BLOCKED_AMENITY_{osm_amenity.upper()}"
        return "EXCLUDE", code, {"amenity": osm_amenity, "name": name}

    osm_office = tags.get("office", "").lower()
    if osm_office in BLOCKED_OSM_OFFICES:
        return "EXCLUDE", f"OSM_BLOCKED_OFFICE_{osm_office.upper()}", {"office": osm_office, "name": name}

    osm_shop = tags.get("shop", "").lower()
    if osm_shop in BLOCKED_OSM_SHOPS:
        return "EXCLUDE", f"OSM_BLOCKED_SHOP_{osm_shop.upper()}", {"shop": osm_shop, "name": name}

    if tags.get("craft") and not any(k in str(tags.get("craft")).lower() for k in ["handicraft", "pottery", "jeweller"]):
        return "EXCLUDE", "OSM_BLOCKED_CRAFT", {"craft": tags.get("craft"), "name": name}

    if tags.get("industrial"):
        return "EXCLUDE", "OSM_BLOCKED_INDUSTRIAL", {"industrial": tags.get("industrial"), "name": name}

    # 3. Overture Blocked Hierarchy Negatives
    hierarchies = candidate.get("taxonomy_hierarchy") or []
    if isinstance(hierarchies, list):
        for h in hierarchies:
            h_clean = str(h).lower().strip().replace(" ", "_")
            if h_clean in blocked_hierarchies:
                return "EXCLUDE", f"OVERTURE_BLOCKED_HIERARCHY_{h_clean.upper()}", {"hierarchy": h_clean, "name": name}

    # 4. Detect Structured Positive Travel Signals (Semantic POI Classification)
    has_core_travel_signal = False
    core_signal_reason = ""
    core_evidence: Dict[str, Any] = {}

    if source == "wikivoyage" or candidate.get("listing_type"):
        has_core_travel_signal = True
        core_signal_reason = "WIKIVOYAGE_TRAVEL_LISTING"
        core_evidence = {"source": "wikivoyage"}
    elif tags.get("tourism") in ("attraction", "museum", "gallery", "viewpoint", "zoo", "theme_park"):
        has_core_travel_signal = True
        core_signal_reason = f"OSM_TOURISM_{tags['tourism'].upper()}"
        core_evidence = {"tourism": tags["tourism"]}
    elif tags.get("historic"):
        has_core_travel_signal = True
        core_signal_reason = f"OSM_HISTORIC_{tags['historic'].upper()}"
        core_evidence = {"historic": tags["historic"]}
    elif tags.get("heritage"):
        has_core_travel_signal = True
        core_signal_reason = "OSM_HERITAGE_TAG"
        core_evidence = {"heritage": tags["heritage"]}
    elif tags.get("leisure") in ("park", "garden", "nature_reserve"):
        has_core_travel_signal = True
        core_signal_reason = f"OSM_LEISURE_{tags['leisure'].upper()}"
        core_evidence = {"leisure": tags["leisure"]}
    elif tags.get("natural") in ("water", "peak", "beach", "cave_entrance"):
        has_core_travel_signal = True
        core_signal_reason = f"OSM_NATURAL_{tags['natural'].upper()}"
        core_evidence = {"natural": tags["natural"]}
    elif candidate.get("wikidata_id") and candidate.get("category") in CORE_TRAVEL_CATEGORIES:
        has_core_travel_signal = True
        core_signal_reason = "WIKIDATA_TRAVEL_ENTITY"
        core_evidence = {"wikidata_id": candidate.get("wikidata_id")}
    else:
        for c in cat_hints:
            c_clean = str(c).lower().strip().replace(" ", "_")
            if c_clean in OVERTURE_TRAVEL_TAXONOMY:
                has_core_travel_signal = True
                core_signal_reason = f"OVERTURE_TRAVEL_{c_clean.upper()}"
                core_evidence = {"taxonomy": c}
                break

    has_secondary_travel_signal = False
    secondary_signal_reason = ""
    secondary_evidence: Dict[str, Any] = {}

    if not has_core_travel_signal:
        if osm_amenity in POSITIVE_OSM_AMENITIES:
            has_secondary_travel_signal = True
            secondary_signal_reason = f"OSM_AMENITY_{osm_amenity.upper()}"
            secondary_evidence = {"amenity": osm_amenity}
        elif tags.get("religion"):
            has_secondary_travel_signal = True
            secondary_signal_reason = "OSM_RELIGIOUS_TAG"
            secondary_evidence = {"religion": tags["religion"]}
        elif tags.get("tourism") in ("hotel", "guest_house", "hostel", "motel"):
            has_secondary_travel_signal = True
            secondary_signal_reason = f"OSM_HOSPITALITY_{tags['tourism'].upper()}"
            secondary_evidence = {"tourism": tags["tourism"]}
        elif tags.get("shop") in ("craft", "art", "books", "confectionery", "pastry", "tea"):
            has_secondary_travel_signal = True
            secondary_signal_reason = f"OSM_TRAVEL_SHOP_{tags['shop'].upper()}"
            secondary_evidence = {"shop": tags["shop"]}
        elif tags.get("craft") in ("handicraft", "pottery", "jeweller"):
            has_secondary_travel_signal = True
            secondary_signal_reason = f"OSM_TRAVEL_CRAFT_{tags['craft'].upper()}"
            secondary_evidence = {"craft": tags["craft"]}
        else:
            for c in cat_hints:
                c_clean = str(c).lower().strip().replace(" ", "_")
                if c_clean in OVERTURE_SECONDARY_TAXONOMY or c_clean in SECONDARY_TRAVEL_CATEGORIES:
                    has_secondary_travel_signal = True
                    secondary_signal_reason = "SECONDARY_COMMERCIAL_PREFILTER"
                    secondary_evidence = {"category": c}
                    break

    # 5. Semantic POI vs Generic Physical Building Type Precedence
    osm_building = tags.get("building", "").lower()
    has_contradictory_building = False
    if osm_building in BLOCKED_OSM_BUILDINGS:
        if has_core_travel_signal or has_secondary_travel_signal:
            # Semantic POI tag exists on this building structure (e.g. shrine in house or ground-floor cafe)
            # Semantic POI meaning dominates generic physical building type!
            has_contradictory_building = True
        else:
            # Pure residential/industrial building with no travel/commercial amenity
            return "EXCLUDE", f"OSM_BLOCKED_BUILDING_{osm_building.upper()}", {"building": osm_building, "name": name}

    # 6. Blocked Name Patterns (Structured Metadata Dominates Business-Name Keywords)
    # If candidate has verified structured travel signals (e.g. amenity=cafe, cuisine=coffee_shop),
    # words like 'warehouse', 'factory', 'bank', 'palace', 'park' inside proper names must NOT trigger exclusion!
    for bp in blocked_patterns:
        m = bp.search(name)
        if m:
            matched_text = m.group(0).lower()
            if has_core_travel_signal or has_secondary_travel_signal:
                if any(w in matched_text for w in ["warehouse", "factory", "bank", "palace", "park", "garden", "studio", "house", "fort", "museum"]):
                    # Structured metadata dominates business-name keyword!
                    continue

            reason_code = "BLOCKED_NAME_PATTERN"
            if any(k in matched_text for k in ["bank", "atm", "cash point"]):
                reason_code = "NON_TRAVEL_FINANCIAL_SERVICE"
            elif any(k in matched_text for k in ["hospital", "clinic", "dispensary", "dental", "medical"]):
                reason_code = "NON_TRAVEL_HEALTHCARE"
            elif any(k in matched_text for k in ["school", "college", "vidyalaya", "academy", "coaching", "tuition"]):
                reason_code = "NON_TRAVEL_EDUCATION"
            elif any(k in matched_text for k in ["courier", "cargo", "packers", "freight", "warehouse"]):
                reason_code = "NON_TRAVEL_LOGISTICS"
            elif any(k in matched_text for k in ["tyre", "tyres", "motor repair", "car repair", "workshop", "garage"]):
                reason_code = "NON_TRAVEL_AUTOMOTIVE_REPAIR"
            elif any(k in matched_text for k in ["apartment", "apartments", "villas", "flats", "builders", "realty", "real estate"]):
                reason_code = "NON_TRAVEL_RESIDENTIAL"
            elif any(k in matched_text for k in ["pvt ltd", "private limited", "limited", "llp", "enterprises", "traders", "consultancy"]):
                reason_code = "NON_TRAVEL_OFFICE_OR_BUSINESS"

            return "EXCLUDE", reason_code, {"name": name, "matched_pattern": m.group(0)}

    # 7. Category Hints Negatives (only if not overridden by positive structured signal)
    if not (has_core_travel_signal or has_secondary_travel_signal):
        for c in cat_hints:
            if not c:
                continue
            c_clean = str(c).lower().strip().replace(" ", "_")
            if c_clean in blocked_categories:
                return "EXCLUDE", f"BLOCKED_CATEGORY_{c_clean.upper()}", {"category": c_clean, "name": name}
            for tok in c_clean.split("_"):
                if tok in blocked_categories:
                    return "EXCLUDE", f"BLOCKED_CATEGORY_TOKEN_{tok.upper()}", {"token": tok, "name": name}

    # 8. Return Validated Travel / Secondary Stages
    if has_core_travel_signal:
        if has_contradictory_building:
            core_evidence["contradictory_building"] = osm_building
        return "TRAVEL_CANDIDATE", core_signal_reason, core_evidence

    if has_secondary_travel_signal:
        if has_contradictory_building:
            secondary_evidence["contradictory_building"] = osm_building
        return "SECONDARY_TRAVEL_CANDIDATE", secondary_signal_reason, secondary_evidence

    # 9. Ambiguous / Review Candidates (Missing categories or unmapped but no negative flags)
    return "REVIEW_CANDIDATE", "UNCLASSIFIED_REQUIRES_RESOLUTION", {"name": name, "cat_hints": cat_hints}


def evaluate_final_relevance(
    place: Dict[str, Any],
    city_meta: Any,
    cat_cfg: Dict[str, Any]
) -> Tuple[str, str, float, Dict[str, Any]]:
    """
    STAGE 2: Final Travel Relevance Decision.
    Evaluates merged consolidated entity after CanonicalPlaceGraph deduplication.
    Returns:
      (decision, reason_code, travel_relevance_score, evidence)
      where decision is:
        - "KEEP": Accepted for final City Pack publication
        - "REVIEW": Genuinely useful ambiguous cases requiring human audit in City Lab
        - "FILTERED": Weak unknown records and unverified generic commercial establishments (traceable in staging diagnostics)
        - "EXCLUDE": High-confidence non-travel junk (banks, hospitals, offices, industrial)
    """
    cat = place.get("category", "unknown")
    subcat = place.get("subcategory", "unclassified")
    name = place.get("name", "")
    name_lower = name.lower()
    sources = [s.get("source") for s in place.get("sources_provenance", [])]
    num_sources = len(place.get("sources_provenance", []))
    qid = place.get("wikidata_id")
    wiki_url = place.get("wikipedia_url")
    wv_image = place.get("commons_image")
    opening_hours = place.get("opening_hours")
    website = place.get("website")
    phone = place.get("phone")
    address = place.get("address")
    raw_tags = place.get("osm_tags") or place.get("tags")
    tags = raw_tags if isinstance(raw_tags, dict) else {}

    # 1. Post-Resolution High-Confidence Negatives Check
    osm_amenity = tags.get("amenity", "").lower()
    if osm_amenity in ("bank", "atm", "bureau_de_change") or any(k in name_lower for k in ["bank branch", "mini atm"]):
        return "EXCLUDE", "NON_TRAVEL_FINANCIAL_SERVICE", 0.0, {"name": name, "amenity": osm_amenity}

    if any(re.search(r"\b" + re.escape(k) + r"\b", name_lower) for k in [
        "hospital", "nursing home", "clinic", "dispensary", "dental clinic",
        "tyre repair", "car repair", "motor repair", "auto spare parts",
        "pvt ltd", "private limited", "packers and movers", "packers & movers"
    ]):
        return "EXCLUDE", "NON_TRAVEL_COMMERCIAL_OR_MEDICAL", 0.0, {"name": name}

    # 2. Unknown / Unclassified Handling
    # Weak unknown records must NOT become human-review work in City Lab!
    if cat in ("unknown", "experience") and subcat in ("unclassified", "general_poi", None):
        if qid and (wiki_url or wv_image):
            return "KEEP", "VERIFIED_WIKIDATA_SIGHT", 0.85, {"wikidata_id": qid, "name": name}
        if "wikivoyage" in sources:
            return "KEEP", "VERIFIED_WIKIVOYAGE_SIGHT", 0.80, {"source": "wikivoyage", "name": name}
        # Filtered from curation: Drop weak unclassified records to diagnostics
        return "FILTERED", "INSUFFICIENT_TRAVEL_EVIDENCE", 0.10, {"name": name, "cat": cat, "sources": sources}

    # 3. Core Travel Destinations (Heritage, Museums, Viewpoints, Nature, Parks, Arts & Culture)
    if cat in CORE_TRAVEL_CATEGORIES:
        score = 0.70
        ev = {"category": cat, "subcategory": subcat}
        if qid and wiki_url:
            score = 1.0
            ev["authority"] = "Wikidata + Wikipedia verified"
        elif qid:
            score = 0.90
            ev["authority"] = f"Wikidata QID: {qid}"
        elif "wikivoyage" in sources:
            score = 0.85
            ev["authority"] = "Wikivoyage travel guide"
        elif "openstreetmap" in sources and num_sources > 1:
            score = 0.80
            ev["authority"] = "Multi-source spatial confirmation"
        elif num_sources > 1:
            score = 0.75
            ev["authority"] = f"Confirmed across {num_sources} providers"

        return "KEEP", "VERIFIED_TRAVEL_DESTINATION", score, ev

    # 4. Secondary Commercial Destinations (Food, Cafe, Shopping, Hotel, Transport, Religious)
    if cat in SECONDARY_TRAVEL_CATEGORIES:
        travel_signals = []
        directory_signals = []
        travel_points = 0
        directory_points = 0.0

        # High-value travel-specific signals
        if qid:
            travel_points += 3
            travel_signals.append("Wikidata presence")
        if wiki_url or wv_image or "wikivoyage" in sources or place.get("source") == "wikivoyage" or place.get("wikivoyage_listing_id") or "wikivoyage_ids" in place.get("external_ids", {}):
            travel_points += 3
            travel_signals.append("Curated travel catalog presence")
        if num_sources > 1:
            travel_points += 2
            travel_signals.append(f"Multi-provider confirmation ({num_sources} sources)")
        if tags.get("tourism") in ("hotel", "hostel", "guest_house", "attraction", "artwork"):
            travel_points += 2
            travel_signals.append("OSM tourism tag")
        if tags.get("historic") or tags.get("heritage"):
            travel_points += 3
            travel_signals.append("Historic or heritage designation")
        if tags.get("craft") in ("handicraft", "pottery", "jeweller") or subcat in ("craft_and_handicraft", "bazaar", "heritage_hotel", "tea_house"):
            travel_points += 2
            travel_signals.append("Recognized craft, bazaar, or specialty venue")
        if tags.get("cuisine") or tags.get("stars"):
            travel_points += 1
            travel_signals.append("Structured cuisine/stars metadata")
        if opening_hours:
            travel_points += 1
            travel_signals.append("Verified opening hours available")

        # Basic directory completeness signals (supporting only)
        if website:
            directory_points += 1.0
            directory_signals.append("Official website verified")
        if address and phone:
            directory_points += 0.5
            directory_signals.append("Contact details complete")

        total_points = travel_points + directory_points

        # Contradictory physical building tag check (e.g. house + shrine/cafe)
        osm_building = tags.get("building", "").lower()
        has_contradictory_building = osm_building in BLOCKED_OSM_BUILDINGS

        # Determine Outcome:
        # A) Auto-KEEP: High travel evidence without contradictory building
        if (travel_points >= 3 or total_points >= 4) and not has_contradictory_building and travel_points >= 1:
            rel_score = min(0.85, 0.50 + (total_points * 0.05))
            return "KEEP", "SECONDARY_COMMERCIAL_ACCEPTED", rel_score, {
                "travel_signals": travel_signals,
                "directory_signals": directory_signals,
                "travel_points": travel_points,
                "total_points": total_points
            }

        # B) Plausibly useful travel content with specific uncertainty -> REVIEW
        # Contradictory building tag (e.g. Natawat Ji Ka Mandir or house cafe)
        if has_contradictory_building and (tags.get("amenity") or tags.get("religion")):
            place["review_priority"] = "HIGH" if (travel_points >= 2 or num_sources > 1) else "MEDIUM"
            place["suggested_action"] = "VERIFY_AMENITY_SIGNIFICANCE"
            return "REVIEW", "CONTRADICTORY_BUILDING_AMENITY", 0.50, {
                "building": osm_building,
                "travel_signals": travel_signals,
                "travel_points": travel_points
            }

        # Secondary destination with genuine travel signals needing human sign-off
        if travel_points >= 2 or (travel_points >= 1 and total_points >= 3):
            place["review_priority"] = "HIGH" if (travel_points >= 2 or num_sources > 1) else "MEDIUM"
            place["suggested_action"] = "APPROVE_AS_SECONDARY_DESTINATION"
            return "REVIEW", "SECONDARY_COMMERCIAL_REQUIRES_AUDIT", 0.45, {
                "travel_signals": travel_signals,
                "directory_signals": directory_signals,
                "travel_points": travel_points,
                "total_points": total_points
            }

        # C) Weak or unverified generic commercial business -> FILTERED
        # (Website + phone alone without travel signals is NOT enough for human review!)
        return "FILTERED", "UNVERIFIED_GENERIC_COMMERCIAL", 0.15, {
            "travel_points": travel_points,
            "total_points": total_points,
            "directory_signals": directory_signals
        }

    # 5. Fallback for other categories
    if qid or "wikivoyage" in sources:
        return "KEEP", "VERIFIED_SPECIAL_DESTINATION", 0.75, {"sources": sources, "qid": qid}
    if num_sources > 1:
        place["review_priority"] = "MEDIUM"
        place["suggested_action"] = "MANUAL_INSPECTION"
        return "REVIEW", "AMBIGUOUS_DESTINATION_EVIDENCE", 0.35, {"name": name, "cat": cat}

    return "FILTERED", "INSUFFICIENT_TRAVEL_EVIDENCE", 0.10, {"name": name, "cat": cat}

