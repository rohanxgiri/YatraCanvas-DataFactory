from pathlib import Path
from datafactory.pipeline.deduplicate import run_deduplicate
from datafactory.utils.text import fuzzy_name_similarity


def test_fuzzy_name_similarity():
    sim1 = fuzzy_name_similarity("City Palace", "City Palace Jaipur")
    assert sim1 >= 0.80

    sim2 = fuzzy_name_similarity("Hawa Mahal", "Albert Hall")
    assert sim2 < 0.50


def test_deduplication_spatial_and_name(tmp_path):
    dup_log = tmp_path / "duplicates.jsonl"
    candidates = [
        {
            "name": "City Palace",
            "latitude": 26.9258,
            "longitude": 75.8237,
            "category": "heritage",
            "source": "overture",
            "source_id": "ov_1",
            "tags": ["heritage"],
        },
        {
            "name": "City Palace Jaipur",
            "latitude": 26.9259,
            "longitude": 75.8238,
            "category": "heritage",
            "source": "openstreetmap",
            "source_id": "osm_1",
            "tags": ["palace"],
            "opening_hours": "09:30-17:00",
        },
        {
            "name": "Nahargarh Fort",
            "latitude": 26.9372,
            "longitude": 75.8155,
            "category": "heritage",
            "source": "overture",
            "source_id": "ov_2",
            "tags": ["fort"],
        }
    ]

    deduped = run_deduplicate(
        classified_places=candidates,
        duplicates_output_path=dup_log,
        city_name="Jaipur",
        state_name="Rajasthan",
        country_name="India"
    )

    # City Palace and City Palace Jaipur should merge into 1 place
    assert len(deduped) == 2
    assert dup_log.exists()

    city_palace = next(p for p in deduped if "City Palace" in p["name"])
    assert city_palace["opening_hours"] == "09:30-17:00"
    assert "yc_in_rj_jaipur_city_palace" in city_palace["canonical_id"]
