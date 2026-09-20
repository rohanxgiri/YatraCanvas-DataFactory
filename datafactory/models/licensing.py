from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class SourceManifestEntry(BaseModel):
    source: str
    dataset_name: str
    dataset_version: str
    license: str
    license_url: str
    attribution: str
    retrieval_date: str
    records_count: int = 0
    source_ids_sample: List[str] = Field(default_factory=list)
    terms_summary: Optional[str] = None


class SourceManifest(BaseModel):
    generated_at: str
    city: str
    country: str
    sources: Dict[str, SourceManifestEntry] = Field(default_factory=dict)
    compliance_notes: List[str] = Field(default_factory=list)


class LicenseManifest(BaseModel):
    city_pack_version: str
    canonical_data_license: str = "Permissive / Mixed provenance with field-level attribution"
    licenses: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    attributions: List[str] = Field(default_factory=list)
