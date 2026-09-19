import json
import pytest
from pathlib import Path
from datafactory.models.place import Place, PlaceTier
from datafactory.sources.geonames_bulk import GeoNamesBulkSource
from datafactory.sources.wikivoyage import WikivoyageSource
from datafactory.pipeline.entity_resolution import CanonicalPlaceGraph
from datafactory.pipeline.score import run_score


def test_geonames_bulk_resolution():
    source = GeoNamesBulkSource()
    meta = source.resolve_city("Jaipur", "Rajasthan", "India")
    assert meta.name == "Jaipur"
    assert meta.state == "Rajasthan"
    assert meta.iso_country == "IN"
    assert 26.5 <= meta.center[0] <= 27.5
    assert 75.5 <= meta.center[1] <= 76.5
    assert len(meta.bbox) == 4
    assert meta.bbox[0] < meta.bbox[2]
    assert meta.bbox[1] < meta.bbox[3]
    assert meta.geonames_id is not None


def test_wikivoyage_listing_parser():
    source = WikivoyageSource()
    sample_wikitext = """
== See ==
* {{see
| name=Amber Fort | alt=Amer Fort
| lat=26.9855 | long=75.8513
| address=Amer, Jaipur
| hours=8AM-6PM
| price=Rs 500
| image=Amber Fort Jaipur.jpg
| wikidata=Q456817
| content=Magnificent hilltop fortress overlooking Maota Lake.
}}
* {{do
| name=Hot Air Balloon Safari
| lat=26.9200 | long=75.8000
| hours=Early morning
| content=Experience Jaipur from above.
}}
* {{eat
| name=Laxmi Mishthan Bhandar
| lat=26.9215 | long=75.8267
| hours=8AM-11PM
| content=Famous for ghewar and traditional sweets.
}}
"""
    listings = source._parse_wikitext_listings(sample_wikitext, "Jaipur")
    assert len(listings) == 3

    # Amber Fort
    fort = next(l for l in listings if "Amber Fort" in l["name"])
    assert fort["suggested_tier"] == "core_destination"
    assert fort["opening_hours"] == "8AM-6PM"
    assert fort["wikidata_id"] == "Q456817"
    assert fort["commons_image"] == "Amber Fort Jaipur.jpg"
    assert fort["prose"]["license"] == "CC-BY-SA-4.0"

    # LMB
    eat = next(l for l in listings if "Laxmi" in l["name"])
    assert eat["suggested_tier"] == "discovery"
    assert eat["category"] == "food"


def test_canonical_place_graph_resolution(tmp_path):
    graph = CanonicalPlaceGraph(city_name="Jaipur", state_name="Rajasthan", country_name="India")

    candidates = [
        {
            "source": "wikivoyage",
            "source_id": "wv_1",
            "name": "Amber Fort",
            "latitude": 26.9855,
            "longitude": 75.8513,
            "category": "heritage",
            "subcategory": "fort",
            "suggested_tier": "core_destination",
            "wikidata_id": "Q456817",
            "opening_hours": "8AM-6PM",
            "opening_hours_source": "wikivoyage",
        },
        {
            "source": "openstreetmap",
            "id": "node/12345",
            "name": "Amer Fort",
            "name_en": "Amber Palace",
            "latitude": 26.9856,
            "longitude": 75.8512,
            "category": "heritage",
            "subcategory": "fort",
            "wikidata_id": "Q456817",
            "tags": {"historic": "fort", "opening_hours": "08:00-18:00"},
        },
        {
            "source": "overture",
            "id": "ov_999",
            "name": "Amber Fort Palace",
            "latitude": 26.9855,
            "longitude": 75.8514,
            "category": "heritage",
            "subcategory": "fort",
        }
    ]

    merges_path = tmp_path / "entity_merges.jsonl"
    canonical = graph.resolve(candidates, merges_path)

    # All 3 records for Amber Fort should merge into ONE canonical place
    assert len(canonical) == 1
    c = canonical[0]
    assert c["name"] == "Amber Fort"
    assert c["tier"] == "core_destination"
    assert c["wikidata_id"] == "Q456817"
    assert c["opening_hours"] == "8AM-6PM"
    assert len(graph.merges_log) == 2


def test_explainable_travel_relevance_scoring():
    places = [
        {
            "canonical_id": "yc_core",
            "name": "Amber Fort",
            "tier": "core_destination",
            "latitude": 26.9855,
            "longitude": 75.8513,
            "category": "heritage",
            "subcategory": "fort",
            "wikidata_id": "Q456817",
            "wikipedia_url": "https://en.wikipedia.org/wiki/Amer_Fort",
            "opening_hours": "8AM-6PM",
            "website": "https://amberfort.org",
            "image_metadata": {"match_method": "wikidata_p18"},
            "sources_provenance": [{"source": "wikivoyage"}, {"source": "openstreetmap"}],
        },
        {
            "canonical_id": "yc_disc",
            "name": "Local Tailor Shop",
            "tier": "discovery",
            "latitude": 26.9100,
            "longitude": 75.8000,
            "category": "shopping",
            "subcategory": "tailor",
            "sources_provenance": [{"source": "overture"}],
        }
    ]

    scored = run_score(places, (75.6, 26.7, 76.0, 27.1))
    core_p = scored[0]
    disc_p = scored[1]

    assert core_p["travel_relevance_score"] >= 0.85
    assert disc_p["travel_relevance_score"] <= 0.30
    assert core_p["prominence_score"] > disc_p["prominence_score"]
    assert core_p["planning"]["indoor_outdoor"] == "outdoor"
    assert core_p["planning"]["rule_version"] in ("2.0", "3.0")
