import pytest
from datafactory.pipeline.classify import vote_category, determine_primary_entity_type
from datafactory.audit.search_engine import CityPackSearchEngine, is_eligible_for_discovery, compute_discovery_score


@pytest.fixture
def empty_source_mappings():
    return {
        "overture": {},
        "osm": {},
    }


def test_hotel_named_garden_inn_remains_hotel(empty_source_mappings):
    candidate = {
        "name": "Collection O Hotel Garden Inn",
        "category_hints": ["hotel"],
        "source": "overture",
    }
    cat, subcat, conf, votes = vote_category(candidate, empty_source_mappings)
    assert cat == "hotel"
    assert subcat == "hotel"
    primary_entity = determine_primary_entity_type(cat, subcat, [], candidate["name"])
    assert primary_entity == "hotel"


def test_hotel_named_parmanand_garden_remains_hotel(empty_source_mappings):
    candidate = {
        "name": "OYO 26659 Hotel Parmanand Garden",
        "category_hints": [],
        "source": "overture",
    }
    cat, subcat, conf, votes = vote_category(candidate, empty_source_mappings)
    assert cat == "hotel"
    assert subcat == "hotel"


def test_hotel_named_heritage_palace_remains_hotel(empty_source_mappings):
    candidate = {
        "name": "Heritage Palace Hotel",
        "category_hints": [],
        "source": "overture",
    }
    cat, subcat, conf, votes = vote_category(candidate, empty_source_mappings)
    assert cat == "hotel"
    assert subcat == "hotel"


def test_hotel_with_cafe_drink_amenity_does_not_become_cafe(empty_source_mappings):
    candidate = {
        "name": "Radisson Hotel Varanasi",
        "listing_type": "drink",
        "source": "wikivoyage",
    }
    cat, subcat, conf, votes = vote_category(candidate, empty_source_mappings)
    assert cat == "hotel"
    assert subcat == "hotel"
    sec_tags = candidate.get("secondary_tags", [])
    assert "cafe" in sec_tags or "bar" in sec_tags


def test_commercial_store_classified_as_shop_not_experience(empty_source_mappings):
    candidate = {
        "name": "A.L store Udaipur",
        "category_hints": [],
        "source": "overture",
    }
    cat, subcat, conf, votes = vote_category(candidate, empty_source_mappings)
    assert cat == "shopping"
    assert subcat == "shop"
    primary_entity = determine_primary_entity_type(cat, subcat, [], candidate["name"])
    assert primary_entity == "shop"


def test_discovery_eligibility_excludes_hotels_and_generic_stores():
    # Hotel must be ineligible
    hotel_place = {
        "name": "OYO 26659 Hotel Parmanand Garden",
        "category": "hotel",
        "primary_entity_type": "hotel",
        "classification": {"category": "hotel", "primary_entity_type": "hotel"},
        "tier": "discovery",
        "location": {"latitude": 24.58, "longitude": 73.68},
        "travel_relevance_score": 0.6,
        "quality": {"overall": 0.8},
    }
    assert not is_eligible_for_discovery(hotel_place)
    assert compute_discovery_score(hotel_place) == 0.0

    # Store must be ineligible
    store_place = {
        "name": "A.L store Udaipur",
        "category": "shopping",
        "primary_entity_type": "shop",
        "classification": {"category": "shopping", "primary_entity_type": "shop"},
        "tier": "discovery",
        "location": {"latitude": 24.58, "longitude": 73.68},
        "travel_relevance_score": 0.6,
        "quality": {"overall": 0.8},
    }
    assert not is_eligible_for_discovery(store_place)
    assert compute_discovery_score(store_place) == 0.0

    # Legitimate heritage/museum attraction is eligible
    attraction_place = {
        "name": "Shilpgram Cultural Village",
        "category": "heritage",
        "primary_entity_type": "tourist_attraction",
        "classification": {"category": "heritage", "primary_entity_type": "tourist_attraction"},
        "tier": "discovery",
        "location": {"latitude": 24.62, "longitude": 73.65},
        "travel_relevance_score": 0.7,
        "quality": {"overall": 0.85},
    }
    assert is_eligible_for_discovery(attraction_place)
    assert compute_discovery_score(attraction_place) > 0.5


def test_search_category_first_ranking_and_no_weak_padding():
    engine = CityPackSearchEngine("mock_city")
    engine.places = [
        {
            "id": "p1",
            "name": "Jaipur Junction Railway Station",
            "classification": {"category": "transport", "subcategory": "station", "primary_entity_type": "railway_station", "tags": ["station", "railway"]},
            "tier": "support",
            "location": {"latitude": 26.92, "longitude": 75.79, "address": "Station Road, Gopalbari"},
            "travel_relevance_score": 0.9,
            "prominence_score": 0.9,
        },
        {
            "id": "p2",
            "name": "Station Road Cafe",
            "classification": {"category": "cafe", "subcategory": "coffee_shop", "primary_entity_type": "cafe", "tags": ["cafe", "coffee"]},
            "tier": "discovery",
            "location": {"latitude": 26.92, "longitude": 75.80, "address": "Station Road, Jaipur"},
            "travel_relevance_score": 0.5,
            "prominence_score": 0.3,
        },
        {
            "id": "p3",
            "name": "Hotel Station View",
            "classification": {"category": "hotel", "subcategory": "hotel", "primary_entity_type": "hotel", "tags": ["hotel", "lodging"]},
            "tier": "support",
            "location": {"latitude": 26.92, "longitude": 75.80, "address": "Near Railway Station, Station Road"},
            "travel_relevance_score": 0.4,
            "prominence_score": 0.2,
        },
    ]

    # Searching for "railway station"
    results = engine.search(query="railway station", limit=10)

    # 1. Actual railway station must be #1
    assert len(results) >= 1
    assert results[0]["id"] == "p1"
    assert results[0]["primary_entity_type"] == "railway_station"

    # 2. "Station Road Cafe" and "Hotel Station View" must NOT rank as railway station (filtered out by intent)
    result_ids = [r["id"] for r in results]
    assert "p2" not in result_ids  # Cafe should not appear in railway station query
    assert "p3" not in result_ids  # Hotel should not appear in railway station query
    # Only 1 legitimate station returned - no padding to 10
    assert len(results) == 1


def test_actual_fort_outranks_hotel_branding():
    engine = CityPackSearchEngine("mock_city")
    engine.places = [
        {
            "id": "f1",
            "name": "Jaigarh Fort",
            "classification": {"category": "heritage", "subcategory": "fort", "primary_entity_type": "fort", "tags": ["fort", "heritage"]},
            "tier": "core_destination",
            "location": {"latitude": 26.98, "longitude": 75.85, "address": "Amer, Jaipur"},
            "travel_relevance_score": 1.0,
            "prominence_score": 1.0,
        },
        {
            "id": "h1",
            "name": "Fort View Heritage Hotel",
            "classification": {"category": "hotel", "subcategory": "hotel", "primary_entity_type": "hotel", "tags": ["hotel"]},
            "tier": "support",
            "location": {"latitude": 26.98, "longitude": 75.85, "address": "Fort Road"},
            "travel_relevance_score": 0.4,
            "prominence_score": 0.2,
        },
    ]

    results = engine.search(query="fort", limit=10)
    assert len(results) >= 1
    assert results[0]["id"] == "f1"
    assert results[0]["category"] == "heritage"
