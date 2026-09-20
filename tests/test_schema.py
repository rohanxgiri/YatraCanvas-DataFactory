import json
import pytest
from pydantic import ValidationError
from datafactory.models.place import Place


def test_place_schema_serialization(sample_place):
    data = sample_place.model_dump()
    assert data["id"] == "yc_in_rj_jaipur_hawa_mahal"
    assert data["name"] == "Hawa Mahal"
    assert data["classification"]["category"] == "heritage"
    assert data["classification"]["subcategory"] == "palace"
    assert data["location"]["latitude"] == 26.9239
    assert data["images"]["primary"]["license"] == "CC BY-SA 4.0"

    # Test roundtrip
    reconstructed = Place(**data)
    assert reconstructed.id == sample_place.id
    assert reconstructed.quality.overall == 0.95


def test_place_schema_validation_error():
    with pytest.raises(ValidationError):
        # Missing required fields like id, name, location, etc.
        Place(id="invalid")
