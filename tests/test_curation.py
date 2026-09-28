import json
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_MODULE_PATH = Path(__file__).parents[1] / "datafactory" / "pipeline" / "curation.py"
_SPEC = importlib.util.spec_from_file_location("datafactory_curation_test_target", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)
CurationApplicationError = _MODULE.CurationApplicationError
apply_human_curation = _MODULE.apply_human_curation
reapply_human_overrides = _MODULE.reapply_human_overrides


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _provider(place_id: str, name: str) -> dict:
    return {
        "canonical_id": place_id,
        "name": name,
        "latitude": 26.9,
        "longitude": 75.8,
        "category": "heritage",
        "tier": "discovery",
        "sources_provenance": [{"source": "openstreetmap"}],
        "image_metadata": None,
        "gallery_metadata": [],
    }


class CurationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_human_curation_survives_provider_refresh_and_carries_media(self) -> None:
        curation = self.root / "curated" / "jaipur"
        media_dir = self.root / "media"
        _write(
            curation / "overrides" / "keep.json",
            {
                "place_id": "keep",
                "verified": True,
                "name": "Human Name",
                "tier": "core_destination",
            },
        )
        _write(
            curation / "exclusions" / "remove.json",
            {"place_id": "remove", "reason": "closed_permanently"},
        )
        _write(
            curation / "additions" / "manual.json",
            {
                "id": "manual",
                "city_id": "jaipur",
                "name": "Manual Place",
                "category": "museum",
                "latitude": 26.91,
                "longitude": 75.81,
                "author": "Editor",
                "evidence_source": "https://example.test/official",
            },
        )
        image_dir = curation / "images" / "keep"
        image_dir.mkdir(parents=True)
        (image_dir / "primary.webp").write_bytes(b"primary")
        (image_dir / "thumbnail.webp").write_bytes(b"thumbnail")
        _write(
            curation / "media" / "keep.json",
            {
                "placeId": "keep",
                "primaryImagePath": "images/keep/primary.webp",
                "thumbnailImagePath": "images/keep/thumbnail.webp",
                "originalFilename": "official.jpg",
                "originalSha256": "a" * 64,
                "source": "Official tourism board",
                "sourcePage": "https://example.test/photo",
                "author": "Photographer",
                "license": "CC BY 4.0",
                "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
                "contributor": "Editor",
                "originalWidth": 1200,
                "originalHeight": 800,
                "primaryWidth": 1200,
                "primaryHeight": 800,
                "importedAt": "2026-09-28T10:00:00Z",
            },
        )

        places, manifest, report = apply_human_curation(
            [_provider("keep", "Fresh Provider Name"), _provider("remove", "Remove")],
            city_id="jaipur",
            curation_dir=curation,
            media_dir=media_dir,
            images_manifest={},
        )

        by_id = {place["canonical_id"]: place for place in places}
        self.assertEqual(set(by_id), {"keep", "manual"})
        self.assertEqual(by_id["keep"]["name"], "Human Name")
        self.assertEqual(by_id["keep"]["tier"], "core_destination")
        self.assertEqual(
            manifest["keep"]["primary"]["match_method"],
            "verified_human_curation",
        )
        self.assertEqual((media_dir / "keep" / "primary.webp").read_bytes(), b"primary")
        self.assertEqual(report.applied_additions, ["manual"])
        self.assertEqual(report.applied_exclusions, ["remove"])

        # Generated scoring may replace the tier; human precedence restores it.
        by_id["keep"]["tier"] = "discovery"
        refreshed = reapply_human_overrides(list(by_id.values()), curation_dir=curation)
        refreshed_by_id = {place["canonical_id"]: place for place in refreshed}
        self.assertEqual(refreshed_by_id["keep"]["tier"], "core_destination")


    def test_orphaned_human_work_fails_closed(self) -> None:
        curation = self.root / "curated" / "jaipur"
        _write(
            curation / "overrides" / "missing.json",
            {"place_id": "missing", "verified": True, "name": "Human Name"},
        )

        with self.assertRaisesRegex(
            CurationApplicationError, "orphaned overrides: missing"
        ) as raised:
            apply_human_curation(
                [_provider("keep", "Provider Name")],
                city_id="jaipur",
                curation_dir=curation,
                media_dir=self.root / "media",
                images_manifest={},
            )
        self.assertIsNotNone(raised.exception.report)
        self.assertEqual(raised.exception.report.orphaned_overrides, ["missing"])

    def test_incomplete_curated_media_fails_closed(self) -> None:
        curation = self.root / "curated" / "jaipur"
        _write(
            curation / "media" / "keep.json",
            {
                "placeId": "keep",
                "primaryImagePath": "images/keep/primary.webp",
                "thumbnailImagePath": "images/keep/thumbnail.webp",
                "originalFilename": "official.jpg",
                "originalSha256": "a" * 64,
                "source": "Official tourism board",
                "sourcePage": "https://example.test/photo",
                "author": "Photographer",
                "license": "CC BY 4.0",
                "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
                "originalWidth": 1200,
                "originalHeight": 800,
                "primaryWidth": 1200,
                "primaryHeight": 800,
                "importedAt": "2026-09-28T10:00:00Z",
            },
        )

        with self.assertRaisesRegex(CurationApplicationError, "contributor"):
            apply_human_curation(
                [_provider("keep", "Provider Name")],
                city_id="jaipur",
                curation_dir=curation,
                media_dir=self.root / "media",
                images_manifest={},
            )


if __name__ == "__main__":
    unittest.main()
