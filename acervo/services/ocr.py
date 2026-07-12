"""OCR services with pluggable adapters (Phase 4, ARCH-009).

Implements OCR via local engines (Tesseract, PaddleOCR) or native PDF
extraction. Each adapter is isolated behind a common interface.
"""

from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path

from acervo.domain.ocr import OcrMethod, OcrResult, TextConfidence, TextRegion


class OcrAdapter(ABC):
    """Abstract OCR engine."""

    @property
    @abstractmethod
    def method_name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @abstractmethod
    def process(self, file_path: str | Path, language: str = "por") -> OcrResult:
        """Return OcrResult with regions and full text."""
        pass


class NativePdfAdapter(OcrAdapter):
    """Extract text directly from PDF without OCR (ARCH-009)."""

    @property
    def method_name(self) -> str:
        return "native_pdf"

    @property
    def version(self) -> str:
        return "1.0"

    def process(self, file_path: str | Path, language: str = "por") -> OcrResult:
        """Attempt native PDF text extraction using pypdf (if available)."""
        start = time.time()
        path = Path(file_path)
        regions: list[TextRegion] = []
        full_text = ""
        errors: list[str] = []
        quality = 0.0

        try:
            # Try pypdf (pure Python, no external deps)
            try:
                from pypdf import PdfReader

                reader = PdfReader(path)
                for page_num, page in enumerate(reader.pages, start=1):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        regions.append(
                            TextRegion(
                                text=page_text,
                                page=page_num,
                                confidence=TextConfidence.HIGH,
                                notes="Extracted from PDF embedded text",
                            )
                        )
                        full_text += f"\n--- Page {page_num} ---\n{page_text}"
                    else:
                        regions.append(
                            TextRegion(
                                text="[no embedded text detected]",
                                page=page_num,
                                confidence=TextConfidence.LOW,
                                notes="Page has no extractable text (image-based or scanned)",
                            )
                        )

                quality = 85.0 if full_text.strip() else 20.0

            except ImportError:
                errors.append("pypdf not installed; install with: pip install pypdf")

        except Exception as exc:
            errors.append(f"PDF extraction failed: {exc}")

        duration = time.time() - start
        return OcrResult(
            file_identifier="",  # set by caller
            method=OcrMethod.NATIVE_PDF,
            method_version=self.version,
            regions=regions,
            full_text=full_text,
            duration_seconds=duration,
            errors=errors,
            quality_score=quality,
        )


class TesseractAdapter(OcrAdapter):
    """OCR via Tesseract (requires installation)."""

    @property
    def method_name(self) -> str:
        return "tesseract"

    @property
    def version(self) -> str:
        return "1.0"

    def process(self, file_path: str | Path, language: str = "por") -> OcrResult:
        """Run Tesseract OCR on an image or PDF page."""
        start = time.time()
        regions: list[TextRegion] = []
        full_text = ""
        errors: list[str] = []
        quality = 0.0

        try:
            import pytesseract
            from PIL import Image

            img = Image.open(file_path)
            text = pytesseract.image_to_string(img, lang=language)
            if text.strip():
                regions.append(
                    TextRegion(
                        text=text,
                        confidence=TextConfidence.MEDIUM,
                        notes="Tesseract OCR",
                    )
                )
                full_text = text
                quality = 70.0
            else:
                errors.append("Tesseract extracted no text")

        except ImportError as exc:
            errors.append(f"Tesseract not available: {exc}. Install: pip install pytesseract pillow")
        except Exception as exc:
            errors.append(f"Tesseract OCR failed: {exc}")

        duration = time.time() - start
        return OcrResult(
            file_identifier="",
            method=OcrMethod.TESSERACT,
            method_version=self.version,
            regions=regions,
            full_text=full_text,
            duration_seconds=duration,
            errors=errors,
            quality_score=quality,
        )


class PaddleOcrAdapter(OcrAdapter):
    """OCR via PaddleOCR (recommended for local use)."""

    @property
    def method_name(self) -> str:
        return "paddle_ocr"

    @property
    def version(self) -> str:
        return "1.0"

    def process(self, file_path: str | Path, language: str = "por") -> OcrResult:
        """Run PaddleOCR on an image."""
        start = time.time()
        regions: list[TextRegion] = []
        full_text = ""
        errors: list[str] = []
        quality = 0.0

        try:
            from paddleocr import PaddleOCR

            # Map language codes (por = Portuguese)
            lang_map = {"por": "pt", "eng": "en", "spa": "es"}
            paddle_lang = lang_map.get(language, "pt")

            ocr = PaddleOCR(use_angle_cls=True, lang=paddle_lang)
            result = ocr.ocr(str(file_path), cls=True)

            if result and result[0]:
                texts = [line[1][0] for line in result[0]]
                full_text = " ".join(texts)

                for line in result[0]:
                    bbox, (text, conf) = line
                    regions.append(
                        TextRegion(
                            text=text,
                            confidence=_confidence_from_score(conf),
                            notes=f"PaddleOCR confidence: {conf:.2f}",
                        )
                    )
                quality = min(100.0, sum(line[1][1] for line in result[0]) / len(result[0]) * 100)
            else:
                errors.append("PaddleOCR returned no results")

        except ImportError as exc:
            errors.append(f"PaddleOCR not available: {exc}. Install: pip install paddleocr")
        except Exception as exc:
            errors.append(f"PaddleOCR failed: {exc}")

        duration = time.time() - start
        return OcrResult(
            file_identifier="",
            method=OcrMethod.PADDLE_OCR,
            method_version=self.version,
            regions=regions,
            full_text=full_text,
            duration_seconds=duration,
            errors=errors,
            quality_score=quality,
        )


def _confidence_from_score(score: float) -> TextConfidence:
    if score > 0.95:
        return TextConfidence.HIGH
    if score > 0.70:
        return TextConfidence.MEDIUM
    return TextConfidence.LOW


# --- Legal entity detection (LEGAL-001) ---

_CNJ_PATTERN = re.compile(
    r"(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})"
)  # NNNNNNN-DD.YYYY.J.TT.OOOO


def detect_cnj_numbers(text: str) -> list[str]:
    """Find and normalize CNJ process numbers in text (LEGAL-001)."""
    return _CNJ_PATTERN.findall(text)


_CPF_PATTERN = re.compile(r"(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})")
_CNPJ_PATTERN = re.compile(r"(\d{2})\.?(\d{3})\.?(\d{3})/? ?(\d{4})-?(\d{2})")
_OAB_PATTERN = re.compile(r"OAB\s*[:/]?\s*(\d+)[./]?(\d+)?", re.IGNORECASE)


def detect_identifiers(text: str) -> dict[str, list[str]]:
    """Detect CPF, CNPJ, and OAB in text."""
    return {
        "cnj_numbers": _CNJ_PATTERN.findall(text),
        "cpf": _CPF_PATTERN.findall(text),
        "cnpj": _CNPJ_PATTERN.findall(text),
        "oab": _OAB_PATTERN.findall(text),
    }
