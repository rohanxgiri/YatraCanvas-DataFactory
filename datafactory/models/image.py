from typing import Optional, List
from pydantic import BaseModel, Field


class ImageMetadata(BaseModel):
    source: str = "Wikimedia Commons"
    source_page: Optional[str] = None
    original_file: str
    author: Optional[str] = None
    license: str
    license_url: Optional[str] = None
    attribution: Optional[str] = None
    width: int = 0
    height: int = 0
    match_method: str = Field(description="wikidata_p18, commons_category, wikipedia_lead, or verified_search")
    match_confidence: float = 0.0
    downloaded_at: str
    local_path: Optional[str] = None
    thumbnail_path: Optional[str] = None


class PlaceImages(BaseModel):
    primary: Optional[ImageMetadata] = None
    gallery: List[ImageMetadata] = Field(default_factory=list)
