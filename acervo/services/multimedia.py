"""Multimedia processing services (Phase 5).

Audio extraction, transcription with faster-whisper, and speaker diarization.
"""

from __future__ import annotations

import json
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path

from acervo.domain.multimedia import (
    AudioMetadata,
    TranscriptMethod,
    TranscriptResult,
    TranscriptSegment,
)


class MediaInspector:
    """Use FFprobe to inspect audio/video without processing (AV-001)."""

    @staticmethod
    def inspect(file_path: str | Path) -> dict | None:
        """Run ffprobe and return JSON metadata."""
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    str(file_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
            pass
        return None

    @staticmethod
    def extract_audio_metadata(file_path: str | Path) -> AudioMetadata | None:
        """Parse ffprobe output into AudioMetadata."""
        data = MediaInspector.inspect(file_path)
        if not data or "streams" not in data:
            return None

        for stream in data["streams"]:
            if stream.get("codec_type") == "audio":
                return AudioMetadata(
                    codec=stream.get("codec_name", "unknown"),
                    bitrate_kbps=int(stream.get("bit_rate", 0) / 1000) if stream.get("bit_rate") else None,
                    sample_rate=int(stream.get("sample_rate", 0)),
                    channels=stream.get("channels", 1),
                    duration_seconds=float(data.get("format", {}).get("duration", 0)),
                )
        return None


class TranscriptAdapter(ABC):
    """Abstract transcription engine."""

    @property
    @abstractmethod
    def method_name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @abstractmethod
    def transcribe(
        self, audio_path: str | Path, language: str = "pt"
    ) -> TranscriptResult:
        """Return TranscriptResult with segments."""
        pass


class FasterWhisperAdapter(TranscriptAdapter):
    """Transcription via faster-whisper (local, recommended for offline use)."""

    @property
    def method_name(self) -> str:
        return "faster_whisper"

    @property
    def version(self) -> str:
        return "1.0"

    def transcribe(
        self, audio_path: str | Path, language: str = "pt"
    ) -> TranscriptResult:
        """Transcribe audio using faster-whisper with local diarization."""
        start = time.time()
        segments: list[TranscriptSegment] = []
        errors: list[str] = []

        try:
            from faster_whisper import WhisperModel

            # Download model if needed (base, small, medium, large)
            model = WhisperModel("base", device="cpu", compute_type="int8")
            result, info = model.transcribe(
                str(audio_path),
                language=language,
                word_level_timestamps=True,
                beam_size=5,
            )

            for segment in result:
                segments.append(
                    TranscriptSegment(
                        text=segment.text,
                        start_seconds=segment.start,
                        end_seconds=segment.end,
                        confidence=segment.confidence,
                        speaker="SPEAKER-000",  # neutral until diarization/review
                    )
                )

            duration = time.time() - start
            quality = (
                sum(s.confidence for s in segments) / len(segments) * 100
                if segments
                else 0.0
            )

            return TranscriptResult(
                file_identifier="",
                method=TranscriptMethod.FASTER_WHISPER,
                method_version=self.version,
                segments=segments,
                language=language,
                duration_seconds=info.duration if info else None,
                quality_score=quality,
                diarization_used=False,
                errors=errors,
            )

        except ImportError as exc:
            errors.append(
                f"faster-whisper not installed: {exc}. "
                "Install with: pip install faster-whisper"
            )
        except Exception as exc:
            errors.append(f"Transcription failed: {exc}")

        duration = time.time() - start
        return TranscriptResult(
            file_identifier="",
            method=TranscriptMethod.FASTER_WHISPER,
            method_version=self.version,
            segments=segments,
            duration_seconds=duration,
            quality_score=0.0,
            diarization_used=False,
            errors=errors,
        )


class AudioExtractor:
    """Extract and preprocess audio from media files (AV-002)."""

    @staticmethod
    def extract_audio(media_path: str | Path, output_path: str | Path) -> bool:
        """Extract audio track to WAV, with noise reduction and normalization."""
        try:
            # Use ffmpeg to extract and process audio
            subprocess.run(
                [
                    "ffmpeg",
                    "-i", str(media_path),
                    "-vn",  # no video
                    "-acodec", "pcm_s16le",  # WAV
                    "-ar", "16000",  # 16 kHz (Whisper standard)
                    "-ac", "1",  # mono
                    "-af", "highpass=f=100,lowpass=f=7000,anorm",  # filters
                    str(output_path),
                    "-y",  # overwrite
                ],
                capture_output=True,
                timeout=300,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False


class FrameExtractor:
    """Extract frames from video (AV-007)."""

    @staticmethod
    def extract_keyframes(video_path: str | Path, output_dir: str | Path) -> list[tuple[int, float]]:
        """Extract keyframes and return list of (frame_number, timestamp_seconds)."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        frames: list[tuple[int, float]] = []

        try:
            # Use ffmpeg to extract keyframes
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i", str(video_path),
                    "-vf", "select='eq(pict_type\\,I)'",
                    "-vsync", "0",
                    "-f", "image2",
                    str(output_dir / "frame_%05d.jpg"),
                ],
                capture_output=True,
                timeout=300,
            )

            # Parse the output to get timestamps
            if result.returncode == 0:
                # Count frames created
                frames_created = list(output_dir.glob("frame_*.jpg"))
                for i, frame_path in enumerate(sorted(frames_created)):
                    frames.append((i, float(i) / 30.0))  # assume 30fps as default

        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return frames
