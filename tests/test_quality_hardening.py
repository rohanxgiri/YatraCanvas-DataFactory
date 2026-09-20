import pytest
from pathlib import Path
from datafactory.pipeline.classify import vote_category, run_classify
from datafactory.pipeline.entity_resolution import CanonicalPlaceGraph
from datafactory.pipeline.score import run_score
from datafactory.pipeline.validate import run_validate_and_quarantine


class TestTaxonomyVoting:
    """Regression tests for category voting on landmark fixtures."""

    def test_lake_palace_not_lake(self):
        candidate = {
            "source": "wikidata",
            "name": "Lake Palace",
            "category": "heritage",
            "subcategory": "palace",
            "wikidata_id": "Q2187746",
        }
        cat, subcat, conf, votes = vote_category(candidate, {})
        assert cat == "heritage"
        assert subcat == "palace"
        assert conf >= 0.85

    def test_city_palace(self):
        candidate = {
            "source": "openstreetmap",
            "name": "City Palace",
            "tags": {"historic": "palace"},
        }
        cat, subcat, conf, votes = vote_category(candidate, {
            "osm": {"historic": {"palace": {"category": "heritage", "subcategory": "palace"}}}
        })
        assert cat == "heritage"
        assert subcat == "palace"

    def test_lake_pichola(self):
        candidate = {
            "source": "wikidata",
            "name": "Lake Pichola",
            "category": "nature",
            "subcategory": "lake",
            "wikidata_id": "Q1800977",
        }
        cat, subcat, conf, votes = vote_category(candidate, {})
        assert cat == "nature"
        assert subcat == "lake"

    def test_central_park(self):
        candidate = {
            "source": "openstreetmap",
            "name": "Central Park",
            "tags": {"leisure": "park"},
        }
        cat, subcat, conf, votes = vote_category(candidate, {
            "osm": {"leisure": {"park": {"category": "park", "subcategory": "garden"}}}
        })
        assert cat == "park"
        assert subcat == "garden"

    def test_albert_hall_museum(self):
        candidate = {
            "source": "wikidata",
            "name": "Albert Hall Museum",
            "category": "museum",
            "subcategory": "history_museum",
            "wikidata_id": "Q4710419",
        }
        cat, subcat, conf, votes = vote_category(candidate, {})
        assert cat == "museum"
        assert subcat == "history_museum"

    def test_metro_station_not_lake(self):
        candidate = {
            "source": "overture",
            "name": "Mansarovar metro station",
            "category_hints": ["transit_station"],
        }
        cat, subcat, conf, votes = vote_category(candidate, {
            "overture": {"transit_station": {"category": "transport", "subcategory": "station"}}
        })
        assert cat == "transport"
        assert cat != "nature"


class TestEntityResolutionConflict:
    """Test entity conflict detection and safe multilingual alias merging."""

    def test_sankat_mochan_vs_durga_mandir_conflict(self, tmp_path):
        graph = CanonicalPlaceGraph("Varanasi", "Uttar Pradesh", "India")
        candidates = [
            {
                "source": "wikivoyage",
                "source_id": "wv_sankat_mochan",
                "name": "Sankat Mochan Hanuman Temple",
                "latitude": 25.2886,
                "longitude": 82.9993,
                "category": "religious",
                "subcategory": "hindu_temple",
                "wikidata_id": "Q19891383",  # Errongous QID in wikitext (actually Durga Mandir)
            },
            {
                "source": "wikidata",
                "source_id": "Q19891383",
                "name": "Durga Mandir, Varanasi",
                "latitude": 25.2886,
                "longitude": 82.9993,
                "category": "religious",
                "subcategory": "hindu_temple",
                "wikidata_id": "Q19891383",
                "name_hi": "दुर्गा मन्दिर",
            }
        ]
        out_path = tmp_path / "merges.jsonl"
        canonical = graph.resolve(candidates, out_path)

        # Must NOT merge into a single entity!
        assert len(canonical) == 2
        # Must record conflict
        assert len(graph.conflicts_log) == 1
        conflict = graph.conflicts_log[0]
        assert "shared_wikidata_id" in conflict["reason_for_conflict"]

        # Sankat Mochan must NOT have Durga Mandir's Hindi name
        sankat = next(p for p in canonical if "Sankat" in p["name"])
        assert sankat.get("name_hi") != "दुर्गा मन्दिर"


class TestCoreDeInflation:
    """Test core destination promotion and de-inflation rules."""

    def test_oyo_hotel_palace_demoted(self):
        places = [
            {
                "canonical_id": "p_oyo_palace",
                "name": "OYO 85823 Ana Palace",
                "category": "heritage",
                "subcategory": "palace",
                "tier": "core_destination",
                "latitude": 26.91,
                "longitude": 75.81,
                "sources_provenance": [{"source": "overture", "source_id": "123"}],
            }
        ]
        city_bbox = (75.7, 26.8, 75.9, 27.0)
        scored = run_score(places, city_bbox)
        assert scored[0]["tier"] != "core_destination"
        assert scored[0]["tier"] in ("support", "discovery")

    def test_true_heritage_retained_in_core(self):
        places = [
            {
                "canonical_id": "p_hawa_mahal",
                "name": "Hawa Mahal",
                "category": "heritage",
                "subcategory": "palace",
                "tier": "core_destination",
                "wikidata_id": "Q836531",
                "latitude": 26.924,
                "longitude": 75.826,
                "sources_provenance": [
                    {"source": "wikivoyage", "source_id": "wv_hawa"},
                    {"source": "wikidata", "source_id": "Q836531"}
                ],
            }
        ]
        city_bbox = (75.7, 26.8, 75.9, 27.0)
        scored = run_score(places, city_bbox)
        assert scored[0]["tier"] == "core_destination"


class TestFieldConfidenceAndSemanticValidation:
    """Test field-level confidence and semantic quarantine."""

    def test_field_confidence_structure(self):
        places = [
            {
                "canonical_id": "p_test",
                "name": "Albert Hall Museum",
                "name_en": "Albert Hall Museum",
                "name_hi": "अल्बर्ट हॉल",
                "category": "museum",
                "subcategory": "history_museum",
                "wikidata_id": "Q4710419",
                "latitude": 26.9118,
                "longitude": 75.8194,
                "opening_hours": "09:00-17:00",
                "opening_hours_source": "openstreetmap",
                "sources_provenance": [{"source": "openstreetmap"}, {"source": "wikidata"}],
            }
        ]
        city_bbox = (75.7, 26.8, 75.9, 27.0)
        scored = run_score(places, city_bbox)
        quality = scored[0]["quality"]
        fc = quality["field_confidence"]
        assert fc["identity_confidence"] >= 0.80
        assert fc["name_confidence"] == 1.0
        assert fc["coordinate_confidence"] == 1.0
        assert fc["opening_hours_confidence"] >= 0.85
        assert "evidence" in fc
        assert "identity" in fc["evidence"]

    def test_semantic_quarantine_lake_station(self, tmp_path):
        places = [
            {
                "canonical_id": "p_bad_lake",
                "name": "Jaipur Railway Station Lake",
                "category": "nature",
                "subcategory": "lake",
                "latitude": 26.91,
                "longitude": 75.81,
                "quality": {"overall": 0.8},
            }
        ]
        city_bbox = (75.7, 26.8, 75.9, 27.0)
        q_path = tmp_path / "quarantine.jsonl"
        accepted, quarantined = run_validate_and_quarantine(places, city_bbox, q_path, tmp_path)
        assert len(accepted) == 0
        assert len(quarantined) == 1
        assert "semantic_conflict" in quarantined[0]["reasons"][0]


class TestHoursAndAnomalyValidation:
    """Test opening hours propagation and anomaly detection scoring."""

    def test_opening_hours_propagation_from_osm_and_wikivoyage(self):
        osm_place = {
            "canonical_id": "p_osm_hrs",
            "name": "Jantar Mantar",
            "category": "heritage",
            "subcategory": "historical_monument",
            "latitude": 26.924,
            "longitude": 75.824,
            "opening_hours": "09:00-16:30",
            "opening_hours_source": "openstreetmap",
            "sources_provenance": [{"source": "openstreetmap"}],
        }
        city_bbox = (75.7, 26.8, 75.9, 27.0)
        scored = run_score([osm_place], city_bbox)
        assert scored[0]["opening_hours"] == "09:00-16:30"
        fc = scored[0]["quality"]["field_confidence"]
        assert fc["opening_hours_confidence"] == 0.90
        assert "osm" in fc["evidence"]["opening_hours"].lower()

    def test_anomaly_scoring_and_flags(self):
        suspicious_place = {
            "canonical_id": "p_anom",
            "name": "Amber Fort OYO Residency",
            "category": "nature",
            "subcategory": "lake",
            "tier": "core_destination",
            "latitude": 26.985,
            "longitude": 75.850,
            "sources_provenance": [{"source": "overture"}],
            "alternate_name_records": [
                {"name": "Different Hotel", "source": "overture", "confidence": 0.20, "is_quarantined": True}
            ],
        }
        city_bbox = (75.7, 26.8, 75.9, 27.0)
        scored = run_score([suspicious_place], city_bbox)
        assert scored[0]["anomaly_score"] > 0.0
        assert len(scored[0]["anomaly_flags"]) > 0

    def test_coordinate_boundary_quarantine(self, tmp_path):
        outside_place = {
            "canonical_id": "p_outside",
            "name": "Delhi Gate in Jaipur",
            "category": "heritage",
            "subcategory": "gate",
            "latitude": 28.65,  # In Delhi, far outside Jaipur bbox (26.7-27.1)
            "longitude": 77.24,
            "quality": {"overall": 0.9},
        }
        city_bbox = (75.7, 26.8, 75.9, 27.0)
        q_path = tmp_path / "quarantine.jsonl"
        accepted, quarantined = run_validate_and_quarantine([outside_place], city_bbox, q_path, tmp_path)
        assert len(accepted) == 0
        assert len(quarantined) == 1
        assert any("bbox" in r or "boundary" in r or "coordinate" in r for r in quarantined[0]["reasons"])
