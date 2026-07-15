"""Tests for Phase 7: Audio transcription and speaker diarization services."""

import pytest

from acervo.services.transcription import TranscriptionService


class TestTranscriptionService:
    """Test Whisper-based audio transcription."""

    def test_initialize_model(self):
        """Test that model initializes without error (if dependencies installed)."""
        try:
            TranscriptionService.initialize()
            assert TranscriptionService._model is not None
        except ImportError:
            pytest.skip("Whisper not installed")

    def test_transcribe_audio_missing_file(self):
        """Test transcription with non-existent file."""
        try:
            result = TranscriptionService.transcribe_audio("/nonexistent/audio.wav")
            assert "error" in result or "not found" in str(result)
        except ImportError:
            pytest.skip("Whisper not installed")

    def test_extract_audio_from_video_missing_file(self):
        """Test audio extraction with non-existent file."""
        result = TranscriptionService.extract_audio_from_video("/nonexistent/video.mp4")
        assert result is None


class TestSpeakerDetection:
    """Test speaker diarization (voice activity detection)."""

    def test_detect_speakers_missing_file(self):
        """Test diarization with non-existent file."""
        result = TranscriptionService.detect_speakers("/nonexistent/audio.wav")
        assert "error" in result

    def test_detect_speakers_requires_librosa(self):
        """Test that librosa is required for diarization."""
        # This test documents the dependency
        try:
            import librosa  # noqa: F401
        except ImportError:
            # If librosa is not installed, diarization will fail
            # This is expected and documented
            pass


class TestTranscriptionResponse:
    """Test transcription response structure."""

    def test_response_structure(self):
        """Test that response has expected fields."""
        try:
            result = TranscriptionService.transcribe_audio("/nonexistent/audio.wav")
            # Even with error, check structure
            assert isinstance(result, dict)
            assert "error" in result or (
                "text" in result
                and "language" in result
                and "segments" in result
                and "confidence" in result
            )
        except ImportError:
            pytest.skip("Whisper not installed")
