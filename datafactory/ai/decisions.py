from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    confidence: float = Field(ge=0, le=1)
    reason_codes: list[str]


class MediaDecision(StrictDecision):
    decision: Literal["ACCEPT", "REJECT", "REVIEW"]
    identity_match: bool
    identity_confidence: float = Field(ge=0, le=1)
    real_photograph: bool
    landmark_prominence: float = Field(ge=0, le=1)
    mobile_card_suitability: float = Field(ge=0, le=1)
    hero_suitability: float = Field(ge=0, le=1)
    watermark_or_obstruction: bool
    wrong_place_risk: float = Field(ge=0, le=1)


class IdentityDecision(StrictDecision):
    decision: Literal["SAME_PLACE", "DIFFERENT_PLACE", "UNRESOLVED"]
    supporting_evidence: list[str]
    conflicting_evidence: list[str]


class HoursDecision(StrictDecision):
    decision: Literal["EXTRACTED", "UNKNOWN"]
    normalized: str | None
    supporting_quotes: list[str]


class DescriptionDecision(StrictDecision):
    decision: Literal["EXTRACTED", "UNKNOWN"]
    description: str | None
    supporting_quotes: list[str]


SCHEMAS = {"media_audit": MediaDecision, "identity_audit": IdentityDecision,
           "hours_extract": HoursDecision, "description_extract": DescriptionDecision}
