from enum import Enum
from typing import Literal, Annotated
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TaskType(str, Enum):
    OPENING_HOURS = "OPENING_HOURS"
    REAL_PRIMARY_IMAGE = "REAL_PRIMARY_IMAGE"
    WEBSITE = "WEBSITE"
    DESCRIPTION = "DESCRIPTION"
    COORDINATE_RESEARCH = "COORDINATE_RESEARCH"
    IDENTITY_RESEARCH = "IDENTITY_RESEARCH"


class Source(StrictModel):
    url: str | None = Field(default=None, max_length=2048)
    source_id: str | None = Field(default=None, max_length=200)
    source_name: str = Field(min_length=1, max_length=200)
    retrieved_at: AwareDatetime
    source_text: str = Field(default="", max_length=5000)
    claimed_quality: str | None = Field(default=None, max_length=40)


class HoursPayload(StrictModel):
    opening_hours: str | None = Field(default=None, max_length=2048)
    source_text: str | None = Field(default=None, max_length=5000)
    source_url: str | None = Field(default=None, max_length=2048)
    source_name: str | None = Field(default=None, max_length=200)
    retrieved_at: AwareDatetime | None = None


class ImagePayload(StrictModel):
    source_page_url: str | None = Field(default=None, max_length=2048)
    direct_media_url: str | None = Field(default=None, max_length=2048)
    local_file: str | None = Field(default=None, max_length=400)
    source_provider: str | None = Field(default=None, max_length=100)
    creator: str | None = Field(default=None, max_length=500)
    license: str | None = Field(default=None, max_length=100)
    license_url: str | None = Field(default=None, max_length=2048)
    attribution: str | None = Field(default=None, max_length=1000)
    notes: str = Field(default="", max_length=2000)


class WebsitePayload(StrictModel):
    website: str | None = Field(default=None, max_length=2048)


class DescriptionPayload(StrictModel):
    description: str | None = Field(default=None, max_length=500)


class CoordinatePoint(StrictModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    source_id: str = Field(min_length=1, max_length=200)
    source_url: str = Field(min_length=1, max_length=2048)


class CoordinatePayload(StrictModel):
    coordinate_sources: list[CoordinatePoint] = Field(default_factory=list, max_length=10)


class IdentityPayload(StrictModel):
    wikidata_id: str | None = Field(default=None, pattern=r"^Q[1-9]\d*$")
    explanation: str = Field(default="", max_length=2000)


class ResultBase(StrictModel):
    task_id: str = Field(pattern=r"^research_[a-f0-9]{24}$")
    place_id: str = Field(min_length=1, max_length=250)
    status: Literal["FOUND", "PARTIAL", "UNRESOLVED", "CONFLICT"]
    sources: list[Source] = Field(default_factory=list, max_length=10)
    research_notes: str = Field(default="", max_length=2000)


class HoursResult(ResultBase):
    type: Literal["OPENING_HOURS"]
    result: HoursPayload


class ImageResult(ResultBase):
    type: Literal["REAL_PRIMARY_IMAGE"]
    result: ImagePayload


class WebsiteResult(ResultBase):
    type: Literal["WEBSITE"]
    result: WebsitePayload


class DescriptionResult(ResultBase):
    type: Literal["DESCRIPTION"]
    result: DescriptionPayload


class CoordinateResult(ResultBase):
    type: Literal["COORDINATE_RESEARCH"]
    result: CoordinatePayload


class IdentityResult(ResultBase):
    type: Literal["IDENTITY_RESEARCH"]
    result: IdentityPayload


ResearchResult = Annotated[HoursResult | ImageResult | WebsiteResult | DescriptionResult |
                           CoordinateResult | IdentityResult, Field(discriminator="type")]


class ResultBundle(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    handoff_id: str = Field(pattern=r"^handoff_[a-f0-9]{24}$")
    results: list[ResearchResult] = Field(max_length=5000)
