"""Explicit human-confirmed, unlicensed local demo media; never verified media."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .image import ImageMetadata


class ManualTestMediaConfirmation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal['1.0'] = '1.0'
    place_id: str
    identity_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    input_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    source_name: str = Field(min_length=1)
    source_page: str
    reference_image_url: str
    original_filename: str
    confirmed_by: str = Field(min_length=1)
    identity_verified: Literal[True]
    real_photograph_confirmed: Literal[True]
    license_verified: Literal[False]
    identity_evidence: list[dict] = Field(min_length=1)
    excluded_entities: list[str] = Field(default_factory=list)


class TestOnlyMediaRecord(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal['1.0'] = '1.0'
    place_id: str
    media_class: Literal['TEST_ONLY_REAL'] = 'TEST_ONLY_REAL'
    usage_scope: Literal['local_testing_only'] = 'local_testing_only'
    license_verified: Literal[False] = False
    identity_verified: Literal[True] = True
    counts_toward_source_readiness: Literal[False] = False
    identity_hash: str
    input_sha256: str
    source_name: str
    source_page: str
    reference_image_url: str
    original_filename: str
    imported_at: str
    confirmed_by: str
    identity_evidence: list[dict]
    excluded_entities: list[str] = Field(default_factory=list)
    primary_sha256: str
    thumbnail_sha256: str
    image: ImageMetadata
