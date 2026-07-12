"""Tests for OCR services (Phase 4)."""

from __future__ import annotations

import re
from pathlib import Path

from acervo.domain.ocr import TextConfidence
from acervo.services.ocr import (
    NativePdfAdapter,
    PaddleOcrAdapter,
    TesseractAdapter,
    detect_cnj_numbers,
    detect_identifiers,
)


def test_native_pdf_adapter_available():
    """Native PDF adapter always available (uses pypdf if present)."""
    adapter = NativePdfAdapter()
    assert adapter.method_name == "native_pdf"
    assert adapter.version == "1.0"


def test_tesseract_adapter_exists():
    """Tesseract adapter can be instantiated (though it requires pytesseract)."""
    adapter = TesseractAdapter()
    assert adapter.method_name == "tesseract"


def test_paddle_ocr_adapter_exists():
    """PaddleOCR adapter can be instantiated (though it requires paddleocr)."""
    adapter = PaddleOcrAdapter()
    assert adapter.method_name == "paddle_ocr"


# --- Legal entity detection (LEGAL-001) ---


def test_detect_cnj_numbers():
    """CNJ process numbers are detected and extracted."""
    text = "Processo nº 0000001-23.2020.1.02.3800 em andamento."
    numbers = detect_cnj_numbers(text)
    assert len(numbers) > 0
    # Format: (NNNNNNN, DD, YYYY, J, TT, OOOO)
    assert numbers[0][0] == "0000001"  # processo number


def test_detect_identifiers():
    """CPF, CNPJ, and OAB are detected in text."""
    text = """
    CPF: 123.456.789-00
    CNPJ: 12.345.678/0001-90
    OAB: 123/SP
    """
    ids = detect_identifiers(text)
    assert len(ids["cpf"]) > 0
    assert len(ids["cnpj"]) > 0
    assert len(ids["oab"]) > 0


def test_cpf_variants():
    """CPF with and without formatting are detected."""
    text = "CPF 123.456.789-00 ou 12345678900"
    ids = detect_identifiers(text)
    assert len(ids["cpf"]) >= 2  # both variants


def test_ocr_result_confidence_levels():
    """Confidence enum values are correct."""
    assert TextConfidence.HIGH.value == "high"
    assert TextConfidence.MEDIUM.value == "medium"
    assert TextConfidence.LOW.value == "low"
    assert TextConfidence.ILLEGIBLE.value == "illegible"
