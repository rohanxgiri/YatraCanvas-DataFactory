from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


class CityRef(BaseModel):
    id: str
    name: str
    state: str
    country: str


class CityMetadata(BaseModel):
    id: str
    name: str
    state: str
    country: str
    iso_country: Optional[str] = "IN"
    center: Tuple[float, float] = Field(description="[latitude, longitude]")
    bbox: Tuple[float, float, float, float] = Field(description="[min_lon, min_lat, max_lon, max_lat]")
    alternate_names: List[str] = Field(default_factory=list)
    timezone: str = "Asia/Kolkata"
    osm_place_id: Optional[int] = None
    geonames_id: Optional[int] = None
    wikidata_id: Optional[str] = None
    dataset_version: str = "1.0.0"
    generated_at: str
    resolution_source: Optional[str] = None
    resolution_confidence: Optional[float] = None

