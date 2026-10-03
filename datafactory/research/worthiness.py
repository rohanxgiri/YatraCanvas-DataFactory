"""Field-specific, deterministic value of research to itinerary users."""
import re
from ..pipeline.media_policy import media_policy, MediaPolicy

ATTRACTIONS = {"heritage", "museum", "religious", "nature", "park", "viewpoint", "arts_culture", "experience", "adventure"}
SCHEDULED = {"museum", "religious", "food", "cafe", "arts_culture", "experience", "adventure"}
CONTROLLED = {"fort", "palace", "stepwell", "garden", "botanical_garden", "zoo", "sanctuary", "amusement_park", "theme_park", "observatory"}
MARKETS = {"bazaar", "craft_market", "night_market", "textile_market", "jewelry_market"}


def research_worthiness(place, kind, *, critical=False):
    tier = place.get("tier", "discovery")
    classification = place.get("classification", {})
    category = classification.get("category", place.get("category"))
    subcategory = classification.get("subcategory")
    core = tier == "core_destination"
    recommended = tier == "recommended"
    prominent = place.get("prominence_score", 0) >= .8
    relevant = place.get("travel_relevance_score", 0) >= .7
    # Existing generic heritage classifications lose the venue subtype. Use names
    # only to establish that visit scheduling is useful, never to invent hours.
    named_venue = category in ATTRACTIONS and bool(re.search(r"\b(museum|temple|mandir|fort|palace|garden|bagh|zoo|observatory)\b", place.get("name", ""), re.I))
    scheduling = category in SCHEDULED or subcategory in CONTROLLED or subcategory in MARKETS or named_venue
    policy = media_policy(place)
    priority, codes = "P4", ["OPTIONAL_METADATA"]
    if kind in {"IDENTITY_RESEARCH", "COORDINATE_RESEARCH"}:
        priority = "P0" if critical or core else "P1"
        codes = ["CRITICAL_IDENTITY_CONFLICT" if kind == "IDENTITY_RESEARCH" else "COORDINATE_OR_REGION_CONFLICT"]
    elif kind == "REAL_PRIMARY_IMAGE":
        if policy == MediaPolicy.REAL_REQUIRED:
            priority, codes = "P0", ["REAL_REQUIRED_IMAGE_MISSING"]
        elif policy == MediaPolicy.REAL_PREFERRED:
            priority = "P1" if prominent and relevant else "P3"
            codes = ["REAL_PREFERRED_IMAGE_MISSING"]
        else:
            return decision(None, ["FALLBACK_ALLOWED_IMAGE"])
    elif tier == "support" or category in {"hotel", "transport", "service"}:
        return decision(None, ["SUPPORT_METADATA"])
    elif kind == "OPENING_HOURS":
        if scheduling and (core or recommended and prominent):
            priority, codes = "P2", ["HOURS_NEEDED_FOR_ITINERARY", "CORE_DESTINATION" if core else "PROMINENT_DESTINATION"]
        elif scheduling and recommended:
            priority, codes = "P3", ["RECOMMENDED_VISIT_SCHEDULING"]
        elif not scheduling:
            return decision(None, ["NO_CONTROLLED_ENTRY_EVIDENCE", "HOURS_NOT_NEEDED_FOR_ITINERARY"])
        else:
            priority, codes = "P4", ["LOW_VALUE_OPTIONAL_HOURS"]
    elif kind == "DESCRIPTION":
        if core and category in ATTRACTIONS or recommended and prominent and relevant and category in ATTRACTIONS:
            priority, codes = "P2", ["DESTINATION_SELECTION_DESCRIPTION"]
        elif recommended and category in ATTRACTIONS and relevant:
            priority, codes = "P3", ["RECOMMENDED_ATTRACTION_DESCRIPTION"]
        else:
            priority, codes = "P4", ["DISCOVERY_POI_DESCRIPTION" if not recommended else "ORDINARY_POI_DESCRIPTION"]
    elif kind == "WEBSITE":
        if (core or recommended and prominent) and scheduling:
            priority, codes = "P2", ["OFFICIAL_SITE_FOR_VISIT_PLANNING"]
        else:
            priority, codes = "P4", ["OPTIONAL_WEBSITE"]
    return decision(priority, codes)


def decision(priority, codes):
    worth = ("DO_NOT_RESEARCH" if priority is None else "RESEARCH_REQUIRED" if priority in {"P0", "P1"}
             else "RESEARCH_RECOMMENDED" if priority in {"P2", "P3"} else "OPTIONAL_DEFER")
    return {"priority": priority or "NO_RESEARCH", "research_worthiness": worth,
            "reason_codes": codes, "why_research": codes if priority in {"P0", "P1", "P2", "P3"} else [],
            "why_not_research": codes if priority in {None, "P4"} else ["DEFERRED_UNTIL_HIGHER_PRIORITIES_RESOLVED"] if priority == "P3" else []}


def task_order(task):
    place = task["place"]
    return (task["priority"], {"core_destination": 0, "recommended": 1, "discovery": 2, "support": 3}.get(place.get("tier"), 4),
            -place.get("travel_relevance_score", 0), -place.get("prominence_score", 0),
            0 if place.get("category") in ATTRACTIONS else 1, task["place_id"], task["type"])
