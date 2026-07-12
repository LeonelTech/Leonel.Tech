"""Integrity & anomaly detection (Phase 8).

Preliminary technical indicators (never "forensic conclusions").
Tracks metadata inconsistencies, possible alterations, and limitations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AnomalyKind(str, Enum):
    """Types of technical indicators that warrant review (INT-001)."""

    # Metadata inconsistencies
    EXTENSION_CONTENT_MISMATCH = "extension_content_mismatch"
    TIMESTAMP_MISMATCH = "timestamp_mismatch"
    METADATA_INCONSISTENCY = "metadata_inconsistency"

    # Encoding / processing anomalies
    UNEXPECTED_REENCODING = "unexpected_reencoding"
    UNEXPECTED_CODEC = "unexpected_codec"
    UNUSUAL_SOFTWARE_TAG = "unusual_software_tag"

    # Audio/video discontinuities
    AUDIO_DISCONTINUITY = "audio_discontinuity"
    ABRUPT_NOISE_FLOOR_CHANGE = "abrupt_noise_floor_change"
    CHANNEL_MISMATCH = "channel_mismatch"
    FRAME_GAP = "frame_gap"
    VARIABLE_FRAMERATE_ANOMALY = "variable_framerate_anomaly"
    DUPLICATED_FRAMES = "duplicated_frames"

    # PDF-specific
    PDF_INCREMENTAL_UPDATE = "pdf_incremental_update"
    INVALID_PDF_SIGNATURE = "invalid_pdf_signature"
    PAGE_REPLACEMENT_INDICATOR = "page_replacement_indicator"

    # Archive anomalies
    ARCHIVE_ANOMALY = "archive_anomaly"
    SUSPICIOUS_COMPRESSION = "suspicious_compression"


class AnomalySeverity(str, Enum):
    """How serious is this indicator (INT-002)."""

    INFO = "info"  # Note for reference
    LOW = "low"  # Benign explanations likely
    MEDIUM = "medium"  # Review recommended
    HIGH = "high"  # Strong indicator of possible alteration


@dataclass(frozen=True)
class IntegrityFinding:
    """A technical indicator warranting human review (INT-001/002)."""

    file_identifier: str
    anomaly_kind: AnomalyKind
    severity: AnomalySeverity
    tool: str  # FFprobe, PDF checker, etc.
    tool_version: str
    confidence: float  # 0-1: how confident is the indicator
    location: str | None = None  # page, timestamp, frame range
    description: str = ""
    benign_explanations: list[str] | None = None  # alternative causes
    review_status: str = "pending"  # pending, reviewed, accepted, dismissed
    notes: str | None = None

    def __post_init__(self):
        if self.benign_explanations is None:
            object.__setattr__(self, "benign_explanations", [])


@dataclass(frozen=True)
class Contradiction:
    """Two assertions that conflict, flagged for review (LEGAL-005)."""

    assertion_1_id: str
    assertion_2_id: str
    conflict_type: str  # "temporal" (same event, different dates), "factual", "named_entity"
    source_1_file: str
    source_2_file: str
    statement_1: str
    statement_2: str
    date_1: str | None = None
    date_2: str | None = None
    confidence: float = 0.5  # 0-1
    review_status: str = "pending"


@dataclass(frozen=True)
class Limitation:
    """Quality or completeness limitation of an analysis (ERR-003)."""

    file_identifier: str
    limitation_type: str  # unsupported_content, missing_metadata, low_confidence…
    description: str
    severity: str = "info"  # info, warning, error
    suggested_action: str = ""  # "manual_review", "external_ai", "skip"
