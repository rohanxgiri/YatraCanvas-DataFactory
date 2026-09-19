import pytest
from pathlib import Path
from datafactory.models.city import CityMetadata, CityRef
from datafactory.models.place import (
    Place,
    PlaceLocation,
    PlaceClassification,
    PlacePlanning,
    PlaceContact,
    PlaceOpeningHours,
    PlaceExternalIds,
    QualityScore,
)
from datafactory.models.image import ImageMetadata, PlaceImages
from datafactory.models.provenance import SourceRecord, FieldProvenance


@pytest.fixture
def sample_city_metadata():
    return CityMetadata(
        id="jaipur",
        name="Jaipur",
        state="Rajasthan",
        country="India",
        iso_country="IN",
        center=(26.9124, 75.7873),
        bbox=(75.658982, 26.755458, 75.978982, 27.075458),
        alternate_names=["Pink City"],
        timezone="Asia/Kolkata",
        generated_at="2026-09-19T10:00:00Z",
    )


@pytest.fixture
def sample_place(sample_city_metadata):
    city_ref = CityRef(
        id=sample_city_metadata.id,
        name=sample_city_metadata.name,
        state=sample_city_metadata.state,
        country=sample_city_metadata.country,
    )
    return Place(
        id="yc_in_rj_jaipur_hawa_mahal",
        name="Hawa Mahal",
        alternate_names=["Palace of Winds"],
        city=city_ref,
        location=PlaceLocation(
            latitude=26.9239,
            longitude=75.8267,
            address="Hawa Mahal Rd, Badi Choupad, Jaipur",
        ),
        classification=PlaceClassification(
            category="heritage",
            subcategory="palace",
            tags=["architecture", "history", "photography", "heritage"],
        ),
        planning=PlacePlanning(
            recommended_visit_minutes=60,
            visit_duration_source="category_heuristic",
            tourism_priority=0.95,
            family_friendly=True,
            best_time="morning",
        ),
        contact=PlaceContact(
            website="https://hawa-mahal.com",
            phone="+911412618862",
        ),
        opening_hours=PlaceOpeningHours(
            raw="09:00-17:00",
            source="openstreetmap",
            verified=False,
        ),
        images=PlaceImages(
            primary=ImageMetadata(
                source="Wikimedia Commons",
                source_page="https://commons.wikimedia.org/wiki/File:Hawa_Mahal_Jaipur.jpg",
                original_file="Hawa_Mahal_Jaipur.jpg",
                author="John Doe",
                license="CC BY-SA 4.0",
                license_url="https://creativecommons.org/licenses/by-sa/4.0",
                attribution="John Doe / Wikimedia Commons",
                width=1920,
                height=1080,
                match_method="wikidata_p18",
                match_confidence=1.0,
                downloaded_at="2026-09-19T10:00:00Z",
                local_path="images/yc_in_rj_jaipur_hawa_mahal/primary.webp",
                thumbnail_path="images/yc_in_rj_jaipur_hawa_mahal/thumbnail.webp",
            ),
            gallery=[],
        ),
        external_ids=PlaceExternalIds(
            overture_id="overture_12345",
            osm_id="way/987654",
            wikidata_id="Q836531",
        ),
        quality=QualityScore(
            overall=0.95,
            identity_confidence=0.98,
            coordinate_confidence=1.0,
            image_confidence=1.0,
            metadata_completeness=0.85,
        ),
        sources=[
            SourceRecord(
                source="overture",
                source_id="overture_12345",
                retrieved_at="2026-09-19T10:00:00Z",
            ),
            SourceRecord(
                source="openstreetmap",
                source_id="way/987654",
                retrieved_at="2026-09-19T10:00:00Z",
            ),
        ],
        provenance_records=[
            FieldProvenance(
                field_name="opening_hours",
                value="09:00-17:00",
                source="openstreetmap",
                source_id="way/987654",
                retrieved_at="2026-09-19T10:00:00Z",
                confidence=0.90,
            )
        ],
        generated_at="2026-09-19T10:00:00Z",
        schema_version="1.0",
    )
