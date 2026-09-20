import pytest
from pathlib import Path
from datafactory.audit.category_coverage import audit_category_coverage
from datafactory.audit.source_recall import audit_source_recall
from datafactory.audit.search_engine import CityPackSearchEngine, compute_discovery_score
from datafactory.audit.search_benchmark import run_search_benchmark
from datafactory.audit.geographic_coverage import audit_geographic_coverage
from datafactory.audit.correctness_audit import audit_data_correctness


class TestAuditSystem:
    """Test suite for City Pack Completeness & Search Audit system."""

    def test_discovery_score_calculation(self):
        # Valid discovery candidate
        place = {
            "tier": "discovery",
            "category": "heritage",
            "classification": {"category": "heritage"},
            "latitude": 26.912,
            "longitude": 75.787,
            "location": {"latitude": 26.912, "longitude": 75.787},
            "travel_relevance_score": 0.80,
            "quality_overall": 0.90,
            "prominence_score": 0.20,
        }
        score = compute_discovery_score(place)
        # (0.80 * 0.4) + (0.90 * 0.4) + (0.80 * 0.2) = 0.32 + 0.36 + 0.16 = 0.84
        assert score == 0.84

        # Hotel or transit should score 0.0
        hotel = dict(place, category="hotel", classification={"category": "hotel"})
        assert compute_discovery_score(hotel) == 0.0

        # Core destination should score 0.0 for discovery candidate score
        core_p = dict(place, tier="core_destination")
        assert compute_discovery_score(core_p) == 0.0

    def test_search_engine_queries(self):
        # Test search on Udaipur
        engine = CityPackSearchEngine("Udaipur", version="v3")
        assert len(engine.places) > 0

        # Query for palace
        palace_results = engine.search(query="palace", limit=5)
        assert len(palace_results) > 0
        assert any("palace" in r["name"].lower() or r["category"] == "heritage" for r in palace_results)

        # Filter by category
        heritage_results = engine.search(category="heritage", limit=5)
        assert len(heritage_results) > 0
        assert all(r["category"] == "heritage" for r in heritage_results)

        # Discovery search
        disc_results = engine.search(tier="discovery", limit=5, discovery_mode=True)
        assert len(disc_results) > 0
        assert all(r["tier"] == "discovery" for r in disc_results)
        assert all(r["discovery_score"] >= 0.0 for r in disc_results)

    def test_geographic_coverage_grid(self):
        geo_rep = audit_geographic_coverage("Udaipur", "Rajasthan", version="v3", grid_size=8)
        assert geo_rep["city"] == "Udaipur"
        summary = geo_rep["summary"]
        assert summary["total_grid_cells"] == 64
        assert summary["non_empty_cells"] > 0
        assert summary["total_released_places"] > 0
        assert Path("reports/udaipur/coverage/geographic_coverage.json").exists()
        assert Path("reports/udaipur/coverage/geographic_coverage.html").exists()

    def test_category_coverage_audit(self):
        cov_rep = audit_category_coverage("Udaipur", "Rajasthan", version="v3")
        assert cov_rep["city"] == "Udaipur"
        summary = cov_rep["summary"]
        assert summary["total_released_places"] > 0
        assert summary["overall_retention_rate_pct"] > 0
        assert "heritage" in cov_rep["categories"]
        assert Path("reports/udaipur/coverage/category_coverage.json").exists()
        assert Path("reports/udaipur/coverage/category_coverage.html").exists()

    def test_data_correctness_and_image_audit(self):
        corr_rep = audit_data_correctness("Udaipur", "Rajasthan", version="v3")
        assert corr_rep["city"] == "Udaipur"
        assert corr_rep["total_places_audited"] > 0
        assert corr_rep["high_severity_issues_count"] == 0
        img_audit = corr_rep["image_audit"]
        assert img_audit["total_images_checked"] > 0
        assert img_audit["disk_verification_pct"] == 100.0
        assert img_audit["category_fallback_images_detected"] == 0
