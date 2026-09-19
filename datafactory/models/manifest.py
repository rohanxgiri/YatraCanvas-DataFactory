from typing import Dict, Optional, Any
from pydantic import BaseModel, Field


class ManifestRecordCounts(BaseModel):
    total_raw_candidates: int = 0
    accepted: int = 0
    rejected: int = 0
    quarantined: int = 0
    duplicate_merges: int = 0
    with_images: int = 0
    with_opening_hours: int = 0
    with_wikidata: int = 0
    category_conflicts: int = 0
    entity_conflicts: int = 0
    alias_conflicts: int = 0
    image_conflicts: int = 0
    coordinate_conflicts: int = 0
    by_tier: Dict[str, int] = Field(default_factory=dict)
    by_tier_stats: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    by_category: Dict[str, int] = Field(default_factory=dict)


class CityManifest(BaseModel):
    schema_version: str = "3.0"
    city_pack_version: str = "v3"
    city_id: str
    city_name: str
    state: str
    country: str
    generated_at: str
    pipeline_health: str = "PASS"  # PASS, WARN, FAIL
    data_quality: str = "PASS"     # PASS, WARN, FAIL
    source_coverage: str = "PASS"  # PASS, WARN, FAIL
    source_versions: Dict[str, str] = Field(default_factory=dict)
    counts: ManifestRecordCounts
    checksums: Dict[str, str] = Field(default_factory=dict)
