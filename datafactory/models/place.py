from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from .city import CityRef
from .image import PlaceImages
from .provenance import SourceRecord, FieldProvenance


class PlaceTier(str, Enum):
    CORE_DESTINATION = "core_destination"
    RECOMMENDED = "recommended"
    DISCOVERY = "discovery"
    SUPPORT = "support"


class PlaceLocation(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None


class PlaceClassification(BaseModel):
    category: str
    subcategory: Optional[str] = None
    primary_entity_type: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class PlacePlanning(BaseModel):
    recommended_visit_minutes: int = 60
    visit_duration_source: str = "category_heuristic"
    rule_version: str = "2.0"
    tourism_priority: float = 0.50
    planning_priority: float = 0.50
    indoor_outdoor: Optional[str] = None  # indoor, outdoor, both
    interest_tags: List[str] = Field(default_factory=list)
    family_friendly: Optional[bool] = None
    best_time: Optional[str] = None


class PlaceContact(BaseModel):
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class PlaceOpeningHours(BaseModel):
    raw: Optional[str] = None
    normalized: Optional[str] = None
    source: Optional[str] = None
    retrieved_at: Optional[str] = None
    confidence: float = 0.0
    verified: bool = False
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)


class PlaceExternalIds(BaseModel):
    overture_id: Optional[str] = None
    osm_id: Optional[str] = None
    wikidata_id: Optional[str] = None
    foursquare_id: Optional[str] = None
    wikivoyage_listing_id: Optional[str] = None
    alltheplaces_id: Optional[str] = None


class FieldConfidence(BaseModel):
    identity_confidence: float = 0.5
    name_confidence: float = 0.5
    coordinate_confidence: float = 0.5
    category_confidence: float = 0.5
    image_confidence: float = 0.0
    opening_hours_confidence: float = 0.0
    evidence: Dict[str, str] = Field(default_factory=dict)


class QualityScore(BaseModel):
    overall: float = 0.0
    identity_confidence: float = 0.0
    coordinate_confidence: float = 0.0
    image_confidence: float = 0.0
    metadata_completeness: float = 0.0
    field_confidence: Optional[FieldConfidence] = None


class Place(BaseModel):
    id: str
    name: str
    name_en: Optional[str] = None
    name_hi: Optional[str] = None
    alternate_names: List[str] = Field(default_factory=list)
    alternate_name_records: List[Dict[str, Any]] = Field(default_factory=list)
    city: CityRef
    location: PlaceLocation
    classification: PlaceClassification
    tier: PlaceTier = PlaceTier.DISCOVERY
    travel_relevance_score: float = 0.0
    prominence_score: float = 0.0
    anomaly_score: float = 0.0
    anomaly_flags: List[str] = Field(default_factory=list)
    planning: PlacePlanning
    contact: PlaceContact
    opening_hours: PlaceOpeningHours
    images: PlaceImages
    external_ids: PlaceExternalIds
    quality: QualityScore
    sources: List[SourceRecord] = Field(default_factory=list)
    provenance_records: List[FieldProvenance] = Field(default_factory=list)
    generated_at: str
    schema_version: str = "3.0"
