"""Tests for multimedia services (Phase 5)."""

from __future__ import annotations

from pathlib import Path

from acervo.domain.multimedia import TranscriptMethod, TranscriptSegment
from acervo.services.multimedia import (
    AudioExtractor,
    FasterWhisperAdapter,
    FrameExtractor,
    MediaInspector,
)


def test_media_inspector_exists():
    """MediaInspector can inspect files (requires ffprobe)."""
    inspector = MediaInspector()
    assert hasattr(inspector, "inspect")
    assert hasattr(inspector, "extract_audio_metadata")


def test_audio_extractor_available():
    """AudioExtractor interface is available."""
    assert callable(AudioExtractor.extract_audio)


def test_frame_extractor_available():
    """FrameExtractor interface is available."""
    assert callable(FrameExtractor.extract_keyframes)


def test_faster_whisper_adapter():
    """FasterWhisperAdapter exists (requires faster-whisper)."""
    adapter = FasterWhisperAdapter()
    assert adapter.method_name == "faster_whisper"
    assert adapter.version == "1.0"


def test_transcript_segment_creation():
    """TranscriptSegment can be created with segments."""
    segment = TranscriptSegment(
        text="Hello world",
        start_seconds=0.0,
        end_seconds=1.5,
        speaker="SPEAKER-001",
        confidence=0.95,
    )
    assert segment.text == "Hello world"
    assert segment.speaker == "SPEAKER-001"
    assert segment.confidence == 0.95
    assert not segment.is_reviewed


def test_transcript_result_creation():
    """TranscriptResult initializes with empty errors if not provided."""
    from acervo.domain.multimedia import TranscriptResult

    result = TranscriptResult(
        file_identifier="FIL-2026-001",
        method=TranscriptMethod.FASTER_WHISPER,
        method_version="1.0",
        segments=[],
    )
    assert result.errors == []
    assert not result.diarization_used
    assert result.language == "pt-BR"
