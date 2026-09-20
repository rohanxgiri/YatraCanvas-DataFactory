import json
from pathlib import Path
from datafactory.models.manifest import CityManifest, ManifestRecordCounts
from datafactory.utils.hashing import compute_sha256


def test_manifest_and_checksum(tmp_path):
    # Create dummy files
    f1 = tmp_path / "file1.txt"
    f1.write_text("hello world", encoding="utf-8")
    sha1 = compute_sha256(f1)
    assert len(sha1) == 64

    counts = ManifestRecordCounts(
        total_raw_candidates=100,
        accepted=50,
        rejected=30,
        quarantined=10,
        duplicate_merges=10,
        with_images=25,
        with_opening_hours=15,
        with_wikidata=20,
        by_category={"heritage": 20, "religious": 15, "food": 15},
    )

    manifest = CityManifest(
        schema_version="1.0",
        city_pack_version="v1",
        city_id="jaipur",
        city_name="Jaipur",
        state="Rajasthan",
        country="India",
        generated_at="2026-09-19T10:00:00Z",
        source_versions={"overture": "latest", "osm": "live"},
        counts=counts,
        checksums={"file1.txt": sha1},
    )

    data = manifest.model_dump()
    assert data["counts"]["accepted"] == 50
    assert data["counts"]["by_category"]["heritage"] == 20
    assert data["checksums"]["file1.txt"] == sha1
