from pathlib import Path
from datafactory.pipeline.validate import run_validate_and_quarantine


def test_quarantine_bad_records(tmp_path):
    city_bbox = (75.6, 26.7, 76.0, 27.1)
    quarantine_log = tmp_path / "quarantined.jsonl"
    media_dir = tmp_path / "media"
    media_dir.mkdir(parents=True)

    places = [
        # Valid place
        {
            "canonical_id": "yc_in_rj_jaipur_valid_place",
            "name": "Valid Place",
            "latitude": 26.9,
            "longitude": 75.8,
            "category": "heritage",
            "quality": {"overall": 0.85},
            "image_metadata": None,
        },
        # Invalid coordinates (outside city)
        {
            "canonical_id": "yc_in_rj_jaipur_outside",
            "name": "Outside City",
            "latitude": 35.0,
            "longitude": 75.8,
            "category": "heritage",
            "quality": {"overall": 0.85},
            "image_metadata": None,
        },
        # Low quality score below threshold
        {
            "canonical_id": "yc_in_rj_jaipur_low_quality",
            "name": "Low Quality Place",
            "latitude": 26.9,
            "longitude": 75.8,
            "category": "food",
            "quality": {"overall": 0.10},
            "image_metadata": None,
        },
    ]

    accepted, quarantined = run_validate_and_quarantine(
        places=places,
        city_bbox=city_bbox,
        quarantine_output_path=quarantine_log,
        media_dir=media_dir
    )

    assert len(accepted) == 1
    assert accepted[0]["canonical_id"] == "yc_in_rj_jaipur_valid_place"
    assert len(quarantined) == 2
    assert quarantine_log.exists()
