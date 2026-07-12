"""OCR and document processing domain (Phase 4).

Represents extracted text regions with bounding boxes, confidence levels,
and uncertainty markers (illegible, partially legible, inferred).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OcrMethod(str, Enum):
    NATIVE_PDF = "native_pdf"  # Embedded text from PDF
    TESSERACT = "tesseract"
    PADDLE_OCR = "paddle_ocr"
    EXTERNAL_AI = "external_ai"


class TextConfidence(str, Enum):
    HIGH = "high"  # >95%
    MEDIUM = "medium"  # 70-95%
    LOW = "low"  # <70%
    ILLEGIBLE = "illegible"


@dataclass(frozen=True)
class TextRegion:
    """A detected text region with bounding box."""

    text: str
    page: int | None = None
    x0: float | None = None  # left
    y0: float | None = None  # top
    x1: float | None = None  # right
    y1: float | None = None  # bottom
    confidence: TextConfidence = TextConfidence.MEDIUM
    is_partial: bool = False
    notes: str | None = None  # e.g. "[partially legible]", "[inferred from context]"


@dataclass(frozen=True)
class OcrResult:
    """Result of OCR on a single file."""

    file_identifier: str
    method: OcrMethod
    method_version: str
    regions: list[TextRegion]
    full_text: str
    duration_seconds: float
    errors: list[str]
    quality_score: float  # 0-100
    model_version: str | None = None
