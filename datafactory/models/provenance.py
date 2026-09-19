from typing import Any, Optional
from pydantic import BaseModel


class SourceRecord(BaseModel):
    source: str
    source_id: Optional[str] = None
    retrieved_at: str
    url: Optional[str] = None
    license: Optional[str] = None


class FieldProvenance(BaseModel):
    field_name: str
    value: Any
    source: str
    source_id: Optional[str] = None
    retrieved_at: str
    confidence: float = 1.0
