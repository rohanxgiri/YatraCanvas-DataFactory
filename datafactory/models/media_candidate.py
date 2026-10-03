from pydantic import BaseModel, ConfigDict, Field


class MediaCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    source_url: str
    media_url: str
    title: str
    creator: str | None = None
    license: str
    license_url: str | None = None
    attribution: str | None = None
    width: int = 0
    height: int = 0
    mime_type: str = "image/jpeg"
    related_entity_id: str | None = None
    commons_category: str | None = None
    source_confidence: float = Field(default=0, ge=0, le=1)
    match_method: str = "contextual_search"
    original_license_verified: bool = False

    @classmethod
    def from_commons(cls, info: dict, method: str, confidence: float, qid=None):
        creator = info.get("author")
        attribution = info.get("attribution")
        if not attribution and creator and creator.lower() != "unknown":
            attribution = f"{creator} / Wikimedia Commons / {info.get('license', '')}"
        return cls(source="Wikimedia Commons", source_url=info.get("source_page") or "",
                   media_url=info.get("url") or "", title=info.get("original_file") or "",
                   creator=creator, license=info.get("license") or "", license_url=info.get("license_url"),
                   attribution=attribution, width=info.get("width", 0), height=info.get("height", 0),
                   mime_type=info.get("mime", ""), related_entity_id=qid, source_confidence=confidence,
                   match_method=method, original_license_verified=True)

    def processing_info(self):
        return {"source": self.source, "original_file": self.title, "url": self.media_url,
                "source_page": self.source_url, "author": self.creator, "license": self.license,
                "license_url": self.license_url, "attribution": self.attribution,
                "width": self.width, "height": self.height, "mime": self.mime_type}
