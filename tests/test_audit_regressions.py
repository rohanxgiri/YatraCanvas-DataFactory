import pytest
import sqlite3
from datafactory.pipeline.classify import vote_category
from datafactory.pipeline.travel_relevance import prefilter_candidate, evaluate_final_relevance
from datafactory.pipeline.completeness import analyze_place_completeness, run_completeness_analysis
from datafactory.sources.wikipedia import WikipediaClient
from datafactory.exporters.sqlite_exporter import export_sqlite
from datafactory.config.settings import get_settings


@pytest.fixture
def cat_cfg():
    return get_settings().category_config


@pytest.fixture
def source_mappings():
    return get_settings().category_config.get("source_mappings", {})


def test_bank_in_mansarovar_excluded_and_not_lake(cat_cfg, source_mappings):
    """
    'Bank of India Mansarovar Branch' with amenity=bank:
    - Must be Stage 1 EXCLUDE with reason NON_TRAVEL_FINANCIAL_SERVICE
    - Must NEVER classify as nature/lake despite containing 'sarovar' in 'Mansarovar'.
    """
    candidate = {
        "name": "Bank of India Mansarovar Branch",
        "tags": {"amenity": "bank"},
        "source": "openstreetmap",
        "source_id": "node/12345",
        "category_hints": ["bank"],
    }
    stage, reason, ev = prefilter_candidate(candidate, cat_cfg)
    assert stage == "EXCLUDE"
    assert reason == "NON_TRAVEL_FINANCIAL_SERVICE"

    # Also test classification voting directly
    cat, subcat, conf, votes = vote_category(candidate, source_mappings)
    assert cat != "nature"
    assert subcat != "lake"


def test_icici_bank_mansarovar_branch_excluded(cat_cfg):
    """'ICICI Bank Mansarovar Branch' must be immediately excluded."""
    candidate = {
        "name": "ICICI Bank Mansarovar Branch",
        "tags": {"amenity": "bank"},
        "source": "openstreetmap",
        "category_hints": ["bank"],
    }
    stage, reason, ev = prefilter_candidate(candidate, cat_cfg)
    assert stage == "EXCLUDE"
    assert "FINANCIAL" in reason


def test_place_in_raja_park_not_park(cat_cfg, source_mappings):
    """
    Places located in 'Raja Park' must not be classified as recreational parks
    purely from the locality name substring.
    """
    candidate = {
        "name": "HDFC Bank Raja Park Branch",
        "tags": {"amenity": "bank"},
        "category_hints": ["bank"],
        "source": "openstreetmap",
    }
    stage, reason, ev = prefilter_candidate(candidate, cat_cfg)
    assert stage == "EXCLUDE"

    cat, subcat, conf, votes = vote_category(candidate, source_mappings)
    assert cat != "park"
    assert subcat != "garden"


def test_actual_lake_containing_sarovar_retained(cat_cfg, source_mappings):
    """
    An actual lake (e.g. Swaroop Sarovar, Mansarovar Lake with natural=water)
    with structured evidence MUST be retained and classified as nature/lake.
    """
    candidate = {
        "name": "Swaroop Sarovar",
        "tags": {"natural": "water", "water": "lake"},
        "source": "openstreetmap",
        "category_hints": ["lake"],
    }
    stage, reason, ev = prefilter_candidate(candidate, cat_cfg)
    assert stage == "TRAVEL_CANDIDATE"

    cat, subcat, conf, votes = vote_category(candidate, source_mappings)
    assert cat == "nature"
    assert subcat == "lake"


def test_actual_park_retained(cat_cfg, source_mappings):
    """
    An actual recreational park with leisure=park MUST be retained and classified as park/garden.
    """
    candidate = {
        "name": "Central Park",
        "tags": {"leisure": "park"},
        "source": "openstreetmap",
        "category_hints": ["park"],
    }
    stage, reason, ev = prefilter_candidate(candidate, cat_cfg)
    assert stage == "TRAVEL_CANDIDATE"

    cat, subcat, conf, votes = vote_category(candidate, source_mappings)
    assert cat == "park"
    assert subcat in ("urban_park", "garden")


def test_unknown_apartment_never_general_poi(cat_cfg, source_mappings):
    """
    An unknown apartment/residential building must be EXCLUDED and never fallback
    to experience / general_poi.
    """
    candidate = {
        "name": "Shree Ram Apartments",
        "tags": {"building": "apartments"},
        "source": "openstreetmap",
        "category_hints": ["apartments"],
    }
    stage, reason, ev = prefilter_candidate(candidate, cat_cfg)
    assert stage == "EXCLUDE"
    assert "RESIDENTIAL" in reason or "BUILDING" in reason

    cat, subcat, conf, votes = vote_category(candidate, source_mappings)
    assert (cat, subcat) != ("experience", "general_poi")
    assert cat == "unknown"


def test_poorly_tagged_monument_recovered_via_wikidata(cat_cfg):
    """
    A poorly tagged legitimate monument with generic tag, when resolved with
    strong Wikidata evidence, must evaluate to KEEP in Stage 2.
    """
    # Raw candidate has no negative tags, so it passes Stage 1 as REVIEW_CANDIDATE
    candidate = {
        "name": "Historic Cenotaph",
        "tags": {},
        "source": "overture",
        "category_hints": [],
    }
    stage, reason, ev = prefilter_candidate(candidate, cat_cfg)
    assert stage == "REVIEW_CANDIDATE"

    # After Entity Resolution, it merges with Wikidata QID and Wikipedia URL
    merged_entity = {
        "canonical_id": "yc_in_rj_jaipur_cenotaph",
        "name": "Historic Cenotaph",
        "category": "heritage",
        "subcategory": "monument",
        "wikidata_id": "Q99999999",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Historic_Cenotaph",
        "sources_provenance": [{"source": "overture"}, {"source": "wikidata"}],
        "tags": {},
    }
    decision, dec_reason, score, evidence = evaluate_final_relevance(
        merged_entity, None, cat_cfg
    )
    assert decision == "KEEP"
    assert dec_reason in ("VERIFIED_TRAVEL_DESTINATION", "VERIFIED_WIKIDATA_SIGHT")
    assert score >= 0.85


def test_stage2_secondary_commercial_thresholds(cat_cfg):
    """
    Secondary commercial POIs:
    - Generic café with 0 signals -> EXCLUDE
    - Cafe with 2 signals (multi-source + website) -> REVIEW
    - Cafe with 3+ signals (Wikidata + website + hours) -> KEEP
    """
    generic_cafe = {
        "canonical_id": "cafe_1",
        "name": "Corner Chai Stall",
        "category": "cafe",
        "subcategory": "cafe",
        "sources_provenance": [{"source": "overture"}],
    }
    dec, rsn, score, ev = evaluate_final_relevance(generic_cafe, None, cat_cfg)
    assert dec == "FILTERED"
    assert rsn == "UNVERIFIED_GENERIC_COMMERCIAL"

    borderline_cafe = {
        "canonical_id": "cafe_2",
        "name": "Good Morning Cafe",
        "category": "cafe",
        "subcategory": "cafe",
        "website": "https://goodmorningcafe.example",
        "sources_provenance": [{"source": "overture"}, {"source": "foursquare"}],
    }
    dec, rsn, score, ev = evaluate_final_relevance(borderline_cafe, None, cat_cfg)
    assert dec == "REVIEW"
    assert rsn == "SECONDARY_COMMERCIAL_REQUIRES_AUDIT"

    verified_cafe = {
        "canonical_id": "cafe_3",
        "name": "Heritage Coffee House",
        "category": "cafe",
        "subcategory": "cafe",
        "wikidata_id": "Q12345678",
        "website": "https://heritagecoffee.example",
        "opening_hours": "07:00-23:00",
        "sources_provenance": [{"source": "overture"}, {"source": "wikidata"}],
    }
    dec, rsn, score, ev = evaluate_final_relevance(verified_cafe, None, cat_cfg)
    assert dec == "KEEP"
    assert rsn == "SECONDARY_COMMERCIAL_ACCEPTED"


def test_completeness_analyzer():
    """
    Test completeness analyzer on complete vs incomplete places.
    """
    complete_place = {
        "name": "Amber Fort",
        "latitude": 26.9855,
        "longitude": 75.8513,
        "tier": "core_destination",
        "category": "heritage",
        "subcategory": "fort",
        "description": "Historic fort complex on a hilltop in Amer, Rajasthan.",
        "primary_image": "images/yc_in_rj_jaipur_amber_fort/primary.webp",
        "opening_hours": "Mo-Su 08:00-17:30",
        "address": "Devisinghpura, Amer, Jaipur, Rajasthan 302001",
        "name_hi": "आमेर क़िला",
        "website": "https://amberfort.org",
        "wikidata_id": "Q361559",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Amber_Fort",
    }
    res = analyze_place_completeness(complete_place)
    assert res["is_complete_critical"] is True
    assert len(res["missing_critical"]) == 0
    assert len(res["missing_recommended"]) == 0
    assert res["completeness_score"] >= 0.90

    incomplete_place = {
        "name": "Random Sight",
        "latitude": 26.9,
        "longitude": 75.8,
        "tier": "core_destination",
        "category": "unknown",
        "subcategory": "unclassified",
    }
    res_inc = analyze_place_completeness(incomplete_place)
    assert res_inc["is_complete_critical"] is False
    assert "category" in res_inc["missing_critical"]
    assert "description" in res_inc["missing_recommended"]
    assert res_inc["completeness_score"] < 0.50



def test_wikipedia_client_extract_cleaning():
    """Test cleaning of raw Wikipedia extract into travel description."""
    client = WikipediaClient()
    raw = (
        "Hawa Mahal (English translation: 'The Palace of Winds' or 'The Palace of Breeze') "
        "is a palace in the city of Jaipur, India.[1][2] Built from red and pink sandstone, "
        "it is on the edge of the City Palace.[3] Its unique five-floor exterior is akin to "
        "the honeycomb of a beehive with its 953 small windows called Jharokhas."
    )
    cleaned = client._clean_extract(raw)
    assert "[1]" not in cleaned
    assert "[2]" not in cleaned
    assert "[3]" not in cleaned
    assert "Hawa Mahal" in cleaned
    assert len(cleaned) <= 500


def test_sqlite_additive_description_schema(tmp_path, sample_city_metadata, sample_place):
    """
    Test that description column is created, queried, and populated
    without breaking backward compatibility.
    """
    db_path = tmp_path / "test_desc_schema.db"
    sample_place.description = "Magnificent palace built of red and pink sandstone."
    export_sqlite(sample_city_metadata, [sample_place], db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Old query (must continue to succeed identically)
    cur.execute("SELECT id, name, category FROM places WHERE id = ?", (sample_place.id,))
    row = cur.fetchone()
    assert row[0] == sample_place.id
    assert row[1] == sample_place.name

    # New additive column query
    cur.execute("SELECT description FROM places WHERE id = ?", (sample_place.id,))
    desc_row = cur.fetchone()
    assert desc_row[0] == "Magnificent palace built of red and pink sandstone."

    conn.close()


def test_the_warehouse_cafe_not_excluded_as_logistics(cat_cfg, source_mappings):
    """
    'The Warehouse Cafe' has amenity=cafe and cuisine tags.
    Structured metadata must dominate name keywords.
    - Must NOT be excluded as NON_TRAVEL_LOGISTICS.
    - Must be SECONDARY_TRAVEL_CANDIDATE.
    - Must classify as cafe.
    """
    candidate = {
        "name": "The Warehouse Cafe",
        "tags": {
            "amenity": "cafe",
            "cuisine": "coffee_shop;chinese;asian;ice_cream;chocolate",
            "opening_hours": "Mo-Su 10:00-20:00",
            "capacity": "45",
        },
        "source": "openstreetmap",
        "category_hints": ["cafe"],
    }
    stage, reason, ev = prefilter_candidate(candidate, cat_cfg)
    assert stage == "SECONDARY_TRAVEL_CANDIDATE"
    assert reason != "NON_TRAVEL_LOGISTICS"

    cat, subcat, conf, votes = vote_category(candidate, source_mappings)
    assert cat == "cafe"
    assert subcat in ("coffee_shop", "cafe")


def test_natawat_ji_ka_mandir_building_house_not_excluded(cat_cfg, source_mappings):
    """
    'Natawat Ji Ka Mandir' has amenity=place_of_worship, religion=hindu, but building=house.
    Semantic POI tag must dominate generic physical building type.
    - Must NOT be excluded as OSM_BLOCKED_BUILDING_HOUSE.
    - Must be SECONDARY_TRAVEL_CANDIDATE.
    - Must classify as religious.
    - In Stage 2, contradictory building tag routes to REVIEW with MEDIUM priority, not dropped!
    """
    candidate = {
        "name": "Natawat Ji Ka Mandir , Jaipur",
        "tags": {
            "amenity": "place_of_worship",
            "religion": "hindu",
            "building": "house",
        },
        "source": "openstreetmap",
        "category_hints": ["place_of_worship"],
    }
    stage, reason, ev = prefilter_candidate(candidate, cat_cfg)
    assert stage == "SECONDARY_TRAVEL_CANDIDATE"
    assert reason != "OSM_BLOCKED_BUILDING_HOUSE"
    assert ev.get("contradictory_building") == "house"

    cat, subcat, conf, votes = vote_category(candidate, source_mappings)
    assert cat == "religious"
    assert subcat in ("hindu_temple", "place_of_worship")

    # Stage 2 evaluation: contradictory building routes to REVIEW for human verification
    place = {
        "name": "Natawat Ji Ka Mandir , Jaipur",
        "category": "religious",
        "subcategory": "hindu_temple",
        "tags": {"amenity": "place_of_worship", "religion": "hindu", "building": "house"},
        "sources_provenance": [{"source": "openstreetmap"}],
    }
    dec, rsn, score, ev = evaluate_final_relevance(place, None, cat_cfg)
    assert dec == "REVIEW"
    assert rsn == "CONTRADICTORY_BUILDING_AMENITY"
    assert place.get("review_priority") in ("HIGH", "MEDIUM")

    # Also test when tags has been transformed to list by classify, but osm_tags is preserved
    place_with_osm_tags = {
        "name": "Natawat Ji Ka Mandir , Jaipur",
        "category": "religious",
        "subcategory": "hindu_temple",
        "tags": ["religious", "hindu_temple"],
        "osm_tags": {"amenity": "place_of_worship", "religion": "hindu", "building": "house"},
        "sources_provenance": [{"source": "openstreetmap"}],
    }
    dec2, rsn2, score2, ev2 = evaluate_final_relevance(place_with_osm_tags, None, cat_cfg)
    assert dec2 == "REVIEW"
    assert rsn2 == "CONTRADICTORY_BUILDING_AMENITY"


def test_nice_cafe_building_house_not_excluded(cat_cfg, source_mappings):
    """
    'Nice Cafe' has amenity=cafe and building=house.
    Semantic POI meaning dominates physical building type.
    """
    candidate = {
        "name": "Nice Cafe",
        "tags": {"amenity": "cafe", "building": "house"},
        "source": "openstreetmap",
        "category_hints": ["cafe"],
    }
    stage, reason, ev = prefilter_candidate(candidate, cat_cfg)
    assert stage == "SECONDARY_TRAVEL_CANDIDATE"
    assert reason != "OSM_BLOCKED_BUILDING_HOUSE"

    cat, subcat, conf, votes = vote_category(candidate, source_mappings)
    assert cat == "cafe"


def test_tours_car_commercial_travel_service_excluded(cat_cfg):
    """
    'Tours Car' is a commercial taxi / car rental booking agency.
    Must be excluded as non-travel transport/service.
    """
    candidate = {
        "name": "Tours Car",
        "source": "overture",
        "category_hints": ["travel_service", "taxi_service"],
        "taxonomy_hierarchy": ["travel_and_transportation", "travel_service", "travel_agent"],
    }
    stage, reason, ev = prefilter_candidate(candidate, cat_cfg)
    assert stage == "EXCLUDE"


def test_real_logistics_warehouse_excluded(cat_cfg):
    """
    An actual commercial warehouse without cafe/travel tags must be excluded as logistics.
    """
    candidate = {
        "name": "Jaipur Logistics Warehouse",
        "tags": {"building": "warehouse"},
        "source": "openstreetmap",
        "category_hints": [],
    }
    stage, reason, ev = prefilter_candidate(candidate, cat_cfg)
    assert stage == "EXCLUDE"
    assert "LOGISTICS" in reason or "BUILDING_WAREHOUSE" in reason


def test_actual_residential_house_excluded(cat_cfg):
    """
    An actual residential house without POI tags must be excluded.
    """
    candidate = {
        "name": "Sharma Niwas",
        "tags": {"building": "house"},
        "source": "openstreetmap",
        "category_hints": [],
    }
    stage, reason, ev = prefilter_candidate(candidate, cat_cfg)
    assert stage == "EXCLUDE"
    assert "BUILDING_HOUSE" in reason


def test_weak_unknown_becomes_filtered_not_review(cat_cfg):
    """
    Weak unclassified records with no travel evidence must be FILTERED,
    NOT dumped into the human REVIEW queue!
    """
    unknown_place = {
        "name": "Some Random Business",
        "category": "unknown",
        "subcategory": "unclassified",
        "sources_provenance": [{"source": "overture"}],
    }
    dec, rsn, score, ev = evaluate_final_relevance(unknown_place, None, cat_cfg)
    assert dec == "FILTERED"
    assert rsn == "INSUFFICIENT_TRAVEL_EVIDENCE"


def test_secondary_commercial_website_and_phone_alone_is_filtered(cat_cfg):
    """
    A generic commercial establishment with only website + phone (and no travel signals)
    must NOT reach REVIEW! It must be FILTERED to protect human curator time.
    """
    generic_cafe = {
        "name": "Generic Local Cafe",
        "category": "cafe",
        "subcategory": "coffee_shop",
        "website": "https://localcafe.example.com",
        "phone": "+919876543210",
        "address": "MI Road, Jaipur",
        "sources_provenance": [{"source": "overture"}],
        "tags": {},
    }
    dec, rsn, score, ev = evaluate_final_relevance(generic_cafe, None, cat_cfg)
    assert dec == "FILTERED"
    assert rsn == "UNVERIFIED_GENERIC_COMMERCIAL"


def test_secondary_commercial_with_multi_provider_and_hours_retained(cat_cfg):
    """
    A secondary destination with cross-source confirmation, verified hours,
    and structured cuisine reaches auto-KEEP or prioritized REVIEW.
    """
    popular_eatery = {
        "name": "LMB Sweets",
        "category": "food",
        "subcategory": "restaurant",
        "opening_hours": "08:00-23:00",
        "tags": {"cuisine": "indian_sweets", "amenity": "restaurant"},
        "sources_provenance": [{"source": "openstreetmap"}, {"source": "overture"}],
        "website": "https://lmbsweets.com",
        "address": "Johari Bazaar, Jaipur",
        "phone": "+911412565844",
    }
    dec, rsn, score, ev = evaluate_final_relevance(popular_eatery, None, cat_cfg)
    assert dec in ("KEEP", "REVIEW")
    if dec == "REVIEW":
        assert popular_eatery.get("review_priority") == "HIGH"

