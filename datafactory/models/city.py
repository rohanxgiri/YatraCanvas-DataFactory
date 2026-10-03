from typing import List, Optional, Tuple, Dict, Any
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
    administrative_ids: Dict[str, str] = Field(default_factory=dict)
    boundary_geometry: Optional[Dict[str, Any]] = None
    region_bbox: Optional[Tuple[float, float, float, float]] = None
    region_geometry: Optional[Dict[str, Any]] = None
    boundary_buffer_m: float = Field(default=0, ge=0)
    region_buffer_m: float = Field(default=0, ge=0)
    source_identifiers: Dict[str, str] = Field(default_factory=dict)

