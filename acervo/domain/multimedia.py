"""Multimedia processing domain (Phase 5).

Audio/video transcription, diarization, frame extraction, and scene detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TranscriptMethod(str, Enum):
    FASTER_WHISPER = "faster_whisper"
    OPENAI_WHISPER = "openai_whisper"
    EXTERNAL_AI = "external_ai"


class DiarizationMethod(str, Enum):
    PYANNOTE = "pyannote"  # open-source
    EXTERNAL_AI = "external_ai"


@dataclass(frozen=True)
class TranscriptSegment:
    """One segment of a transcript (typically sentence-level)."""

    text: str
    start_seconds: float
    end_seconds: float
    speaker: str = "SPEAKER-000"  # neutral label until reviewed
    confidence: float = 0.5  # 0-1
    is_reviewed: bool = False  # human-confirmed speaker identity
    notes: str | None = None


@dataclass(frozen=True)
class TranscriptResult:
    """Full transcript of an audio/video file."""

    file_identifier: str
    method: TranscriptMethod
    method_version: str
    segments: list[TranscriptSegment]
    language: str = "pt-BR"
    duration_seconds: float | None = None
    quality_score: float = 0.0  # 0-100
    diarization_used: bool = False
    model_version: str | None = None
    errors: list[str] | None = None

    def __post_init__(self):
        if self.errors is None:
            object.__setattr__(self, "errors", [])


@dataclass(frozen=True)
class FrameMetadata:
    """Metadata for an extracted video frame."""

    frame_number: int
    timestamp_seconds: float
    width: int
    height: int
    has_scene_change: bool = False
    visual_description: str | None = None


@dataclass(frozen=True)
class AudioMetadata:
    """Audio stream metadata from FFprobe."""

    codec: str
    bitrate_kbps: int | None
    sample_rate: int
    channels: int
    duration_seconds: float
    loudness_lufs: float | None = None
