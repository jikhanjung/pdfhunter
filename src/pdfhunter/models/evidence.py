"""Evidence data models for tracking extraction sources."""

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    """Type of evidence source."""

    OCR_TEXT = "ocr_text"
    PDF_TEXT = "pdf_text"
    IMAGE_CAPTURE = "image_capture"
    WEB_SEARCH = "web_search"
    USER_INPUT = "user_input"


class BoundingBox(BaseModel):
    """Bounding box coordinates for text location."""

    x1: float
    y1: float
    x2: float
    y2: float

    def to_list(self) -> list[float]:
        return [self.x1, self.y1, self.x2, self.y2]


class Evidence(BaseModel):
    """Evidence record for an extracted field."""

    field_name: str
    value: Any = None
    evidence_type: EvidenceType
    page_number: int | None = None
    source_text: str | None = None
    bbox: BoundingBox | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    image_path: Path | None = None
    web_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "field_name": self.field_name,
            "value": self.value,
            "evidence_type": self.evidence_type.value,
            "confidence": self.confidence,
        }
        if self.page_number is not None:
            result["page_number"] = self.page_number
        if self.source_text:
            result["source_text"] = self.source_text
        if self.bbox:
            result["bbox"] = self.bbox.to_list()
        if self.image_path:
            result["image_path"] = str(self.image_path)
        if self.web_url:
            result["web_url"] = self.web_url
        if self.metadata:
            result["metadata"] = self.metadata
        return result
