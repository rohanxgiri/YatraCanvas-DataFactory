import pytest
from unittest.mock import patch, MagicMock

from datafactory.sources.geonames_bulk import GeoNamesBulkSource, CityNotFoundInRequestedState
from datafactory.pipeline.city_resolver import CityResolutionPipeline, CityResolutionConflict
from datafactory.sources.wikivoyage import WikivoyageSource
from datafactory.pipeline.classify import (
    vote_category,
    determine_primary_entity_type,
    has_structured_transport_evidence
)
from datafactory.pipeline.entity_resolution import CanonicalPlaceGraph


class TestResolverHardening:
    """Deterministic regression tests for city resolution, constraints, and fallback."""

    def test_same_city_name_in_multiple_states_requested_state_wins(self):
        """When a city exists in multiple states (e.g. Manali in Tamil Nadu), requesting Tamil Nadu must return TN."""
        source = GeoNamesBulkSource()
        meta = source.resolve_city(city_name="Manali", state_name="Tamil Nadu", country_name="India")
        assert meta.state == "Tamil Nadu"
        assert meta.country == "India"
        assert 12.5 <= meta.center[0] <= 13.5  # Chennai latitude

    def test_missing_city_in_requested_state_raises_exception_and_does_not_fall_back(self):
        """When Manali is requested in Himachal Pradesh, GeoNames cities15000 must NOT silently return TN."""
        source = GeoNamesBulkSource()
        with pytest.raises(CityNotFoundInRequestedState) as excinfo:
            source.resolve_city(city_name="Manali", state_name="Himachal Pradesh", country_name="India")
        assert "CITY_NOT_FOUND_IN_REQUESTED_STATE" in str(excinfo.value)

    def test_small_town_fallback_resolves_manali_hp(self):
        """Small tourism town fallback resolves Manali, HP through Nominatim/OSM or Wikidata."""
        resolver = CityResolutionPipeline()
        meta = resolver.resolve(city_name="Manali", state_name="Himachal Pradesh", country_name="India")
        assert meta.name == "Manali"
        assert meta.state == "Himachal Pradesh"
        assert meta.country == "India"
        assert 32.0 <= meta.center[0] <= 32.5  # Himalayan town latitude
        assert 77.0 <= meta.center[1] <= 77.5  # Himalayan town longitude
        assert meta.resolution_source in ("nominatim_osm", "osm_overpass_boundary", "wikidata")
        assert meta.resolution_confidence >= 0.85

    def test_contradictory_resolver_sources_stops_build(self):
        """If resolver candidates disagree on state or coordinates by >50km, raise CityResolutionConflict."""
        resolver = CityResolutionPipeline()
        cand1 = {
            "source": "source_a",
            "meta": MagicMock(state="Himachal Pradesh", country="India", center=(32.24, 77.18), bbox=(77.1, 32.1, 77.3, 32.3), resolution_source="a", resolution_confidence=0.9),
            "lat": 32.24,
            "lon": 77.18,
            "state": "Himachal Pradesh",
            "country": "India",
            "confidence": 0.9
        }
        cand2 = {
            "source": "source_b",
            "meta": MagicMock(state="Himachal Pradesh", country="India", center=(13.16, 80.26), bbox=(80.1, 13.0, 80.4, 13.3), resolution_source="b", resolution_confidence=0.8),
            "lat": 13.16,
            "lon": 80.26,
            "state": "Himachal Pradesh",
            "country": "India",
            "confidence": 0.8
        }
        with pytest.raises(CityResolutionConflict) as excinfo:
            resolver._perform_consistency_check("Manali", "Himachal Pradesh", "India", [cand1, cand2])
        assert "CITY_RESOLUTION_CONFLICT" in str(excinfo.value)
        assert "Spatial coordinates disagree" in str(excinfo.value)

    def test_state_mismatch_stops_build(self):
        """Candidate state mismatch against requested state raises CityResolutionConflict."""
        resolver = CityResolutionPipeline()
        cand = {
            "source": "geonames",
            "meta": MagicMock(),
            "lat": 13.16,
            "lon": 80.26,
            "state": "Tamil Nadu",
            "country": "India",
            "confidence": 0.9
        }
        with pytest.raises(CityResolutionConflict) as excinfo:
            resolver._perform_consistency_check("Manali", "Himachal Pradesh", "India", [cand])
        assert "contradicts requested state" in str(excinfo.value)


class TestWikivoyageTitleNormalization:
    """Deterministic regression tests for Wikivoyage title normalization."""

    def test_diacritic_ascii_mediawiki_title_lookup(self):
        """Rishīkesh (with macron) resolves to ASCII 'Rishikesh'."""
        wv = WikivoyageSource()
        title_res = wv.resolve_article_title("Rishīkesh")
        assert title_res is not None
        resolved_title, wikitext = title_res
        assert resolved_title == "Rishikesh"
        assert len(wikitext) > 1000


class TestTransitClassificationHardening:
    """Deterministic regression tests for transit classification hardening."""

    def test_station_road_pharmacy_not_railway_station(self):
        """Apollo Pharmacy Railway Station Road Rishikesh must be classified as shopping, not railway_station."""
        candidate = {
            "source": "overture",
            "name": "Apollo Pharmacy Railway Station Road Rishikesh",
            "category_hints": ["pharmacy", "health_care"],
            "tags": {}
        }
        cat, subcat, conf, votes = vote_category(candidate, source_mappings={})
        entity_type = determine_primary_entity_type(
            category=cat,
            subcategory=subcat,
            tags=candidate.get("tags"),
            name=candidate.get("name")
        )
        assert cat == "shopping"
        assert entity_type in ("shop", "pharmacy")
        assert entity_type != "railway_station"
        assert not has_structured_transport_evidence(candidate)

    def test_travel_junction_business_not_transport_hub(self):
        """Goa Travels Junction without structured transit evidence must NOT be classified as transport."""
        candidate = {
            "source": "overture",
            "name": "Goa Travels Junction",
            "category_hints": ["travel_agency", "service"],
            "tags": {}
        }
        cat, subcat, conf, votes = vote_category(candidate, source_mappings={})
        entity_type = determine_primary_entity_type(
            category=cat,
            subcategory=subcat,
            tags=candidate.get("tags"),
            name=candidate.get("name")
        )
        assert cat != "transport"
        assert entity_type != "railway_station"
        assert entity_type != "transport_hub"

    def test_structured_railway_station_is_classified_as_railway_station(self):
        """A genuine station with structured OSM railway=station tag is classified as railway_station."""
        candidate = {
            "source": "openstreetmap",
            "name": "Rishikesh Railway Station",
            "tags": {"railway": "station"},
            "category_hints": ["train_station"]
        }
        assert has_structured_transport_evidence(candidate)
        source_mappings = {
            "osm": {
                "railway": {
                    "station": {"category": "transport", "subcategory": "station"}
                }
            }
        }
        cat, subcat, conf, votes = vote_category(candidate, source_mappings=source_mappings)
        entity_type = determine_primary_entity_type(
            category=cat,
            subcategory=subcat,
            tags=candidate.get("tags"),
            name=candidate.get("name")
        )
        assert cat == "transport"
        assert entity_type == "railway_station"


class TestNameConflictDiagnostics:
    """Deterministic regression tests for neighboring entity disambiguation."""

    def test_neighboring_restaurants_with_distinct_names_do_not_merge(self):
        """Neighboring restaurants within 25m ('Ganga Jamuna Restaurant' vs 'Mamta Restaurant') must NOT merge."""
        graph = CanonicalPlaceGraph(city_name="Rishikesh", state_name="Uttarakhand", country_name="India")
        base = {
            "source": "overture",
            "source_id": "base-1",
            "name": "Ganga Jamuna Restaurant",
            "category": "food",
            "subcategory": "restaurant",
            "latitude": 30.126709,
            "longitude": 78.326898,
        }
        cand = {
            "source": "overture",
            "source_id": "cand-2",
            "name": "Mamta Restaurant",
            "category": "food",
            "subcategory": "restaurant",
            "latitude": 30.126850,
            "longitude": 78.326920,  # ~16 meters apart
        }
        is_dup, reason, conf, conflict = graph._check_entity_agreement(base, cand)
        assert is_dup is False, f"Expected is_dup=False for distinct neighboring businesses, got {is_dup} ({reason})"
