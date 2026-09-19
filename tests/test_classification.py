from pathlib import Path
from datafactory.pipeline.classify import run_classify
from datafactory.pipeline.normalize import run_normalize_and_filter


def test_category_classification():
    candidates = [
        {
            "source": "overture",
            "name": "Amber Fort",
            "category_hints": ["fort", "castle"],
            "tags": [],
        },
        {
            "source": "openstreetmap",
            "name": "Albert Hall Museum",
            "tags": {"tourism": "museum"},
        },
        {
            "source": "openstreetmap",
            "name": "Govind Dev Ji Temple",
            "tags": {"amenity": "place_of_worship", "religion": "hindu"},
        }
    ]

    classified = run_classify(candidates)
    assert len(classified) == 3

    # Amber Fort
    c0 = classified[0]
    assert c0["category"] == "heritage"
    assert c0["subcategory"] == "fort"
    assert "heritage" in c0["tags"]

    # Albert Hall Museum
    c1 = classified[1]
    assert c1["category"] == "museum"
    assert c1["subcategory"] == "history_museum"

    # Govind Dev Ji Temple
    c2 = classified[2]
    assert c2["category"] == "religious"
    assert c2["subcategory"] == "hindu_temple"


def test_rejection_filtering(tmp_path):
    overture_sample = [
        {"name": "State Bank of India ATM", "basic_category": "atm"},
        {"name": "Allen Career Institute Coaching", "basic_category": "educational_institution"},
        {"name": "Jal Mahal Parking Lot", "basic_category": "parking"},
        {"name": "Hawa Mahal", "basic_category": "palace", "latitude": 26.92, "longitude": 75.82},
    ]

    rejected_log = tmp_path / "rejected.jsonl"
    accepted = run_normalize_and_filter(overture_sample, [], rejected_log)

    # Only Hawa Mahal should pass
    assert len(accepted) == 1
    assert accepted[0]["name"] == "Hawa Mahal"
    assert rejected_log.exists()
