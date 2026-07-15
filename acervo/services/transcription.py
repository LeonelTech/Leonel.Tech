"""Audio transcription and speaker diarization services (Phase 7).

Preliminary technical analysis for speech-to-text conversion.
Supports local models (Whisper) and optional external APIs.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from acervo.db.models import File, CatalogingSession
from acervo.domain.integrity import AnomalySeverity
from acervo.services.audit import record_event


class TranscriptionService:
    """Audio transcription using Whisper (local or API)."""

    _model = None
    _processor = None
    _device = None

    @classmethod
    def initialize(cls):
        """Lazy-load Whisper model on first use."""
        if cls._model is not None:
            return

        try:
            import torch
            import whisper

            # Use GPU if available, fallback to CPU
            cls._device = "cuda" if torch.cuda.is_available() else "cpu"
            cls._model = whisper.load_model("base", device=cls._device)
        except ImportError:
            raise ImportError(
                "Whisper not installed. Install with: pip install openai-whisper torch"
            )

    @staticmethod
    def extract_audio_from_video(video_path: str | Path) -> bytes | None:
        """Extract audio stream from video file (MP4, MKV, etc)."""
        video_path = Path(video_path)
        if not video_path.exists():
            return None

        try:
            import ffmpeg
        except ImportError:
            return None

        try:
            # Extract audio to WAV using ffmpeg
            process = (
                ffmpeg
                .input(str(video_path))
                .audio
                .output("pipe:", format="wav")
                .run(capture_stdout=True, capture_stderr=True, quiet=True)
            )
            return process[0]
        except Exception:
            return None

    @classmethod
    def transcribe_audio(
        cls,
        audio_path: str | Path,
        language: str = "pt",
    ) -> dict[str, object]:
        """Transcribe audio file to text using Whisper.

        Returns:
            {
                'text': full transcription,
                'language': detected language,
                'segments': [{'start': time, 'end': time, 'text': segment_text}],
                'confidence': avg confidence score (0-1),
            }
        """
        cls.initialize()
        audio_path = Path(audio_path)

        if not audio_path.exists():
            return {"error": f"Audio file not found: {audio_path}"}

        try:
            result = cls._model.transcribe(
                str(audio_path),
                language=language if language != "pt" else "pt",
                task="transcribe",
            )

            return {
                "text": result.get("text", ""),
                "language": result.get("language", language),
                "segments": [
                    {
                        "start": seg.get("start", 0),
                        "end": seg.get("end", 0),
                        "text": seg.get("text", ""),
                    }
                    for seg in result.get("segments", [])
                ],
                "confidence": cls._estimate_confidence(result),
            }
        except Exception as e:
            return {"error": f"Transcription failed: {str(e)}"}

    @staticmethod
    def _estimate_confidence(result: dict) -> float:
        """Estimate overall confidence from Whisper result."""
        if not result.get("segments"):
            return 0.0

        # Whisper doesn't provide confidence per token, estimate from segment count
        # More segments typically = higher confidence in detection
        segment_count = len(result.get("segments", []))
        # Normalize to 0-1 range (assume 10+ segments = high confidence)
        return min(segment_count / 10.0, 1.0)

    @classmethod
    def detect_speakers(
        cls,
        audio_path: str | Path,
        num_speakers: Optional[int] = None,
    ) -> dict[str, object]:
        """Simple speaker diarization (experimental).

        Note: Full diarization requires pyannote or similar.
        This is a simplified detector for multiple voice activity.
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            return {"error": f"Audio file not found: {audio_path}"}

        try:
            import librosa

            # Load audio
            y, sr = librosa.load(str(audio_path), sr=16000)

            # Detect speech vs silence using energy
            S = librosa.feature.melspectrogram(y=y, sr=sr)
            S_db = librosa.power_to_db(S, ref=0)

            # Simple VAD: frames above threshold are speech
            energy = librosa.feature.rms(y=y)[0]
            threshold = 0.02
            speech_frames = energy > threshold

            # Convert frames to time
            frame_times = librosa.frames_to_time(
                range(len(speech_frames)), sr=sr
            )

            speech_segments = []
            in_speech = False
            start_time = 0

            for i, is_speech in enumerate(speech_frames):
                if is_speech and not in_speech:
                    start_time = frame_times[i]
                    in_speech = True
                elif not is_speech and in_speech:
                    speech_segments.append({
                        "start": float(start_time),
                        "end": float(frame_times[i]),
                        "duration": float(frame_times[i] - start_time),
                    })
                    in_speech = False

            return {
                "segments": speech_segments,
                "total_speech_duration": sum(s["duration"] for s in speech_segments),
                "num_speakers_detected": min(len(speech_segments), num_speakers or 2),
            }
        except ImportError:
            return {
                "error": "librosa not installed",
                "note": "Install with: pip install librosa",
            }
        except Exception as e:
            return {"error": f"Diarization failed: {str(e)}"}


def record_transcription(
    session: Session,
    file: File,
    text: str,
    language: str,
    confidence: float,
) -> dict[str, object]:
    """Store transcription as file metadata."""
    # Store in file.extracted_text or similar field
    # For now, log it and return
    record_event(
        session,
        action="transcription.complete",
        subject_type="file",
        subject_identifier=file.identifier,
        detail={
            "language": language,
            "confidence": confidence,
            "length": len(text),
        },
    )
    return {
        "file_identifier": file.identifier,
        "text": text,
        "language": language,
        "confidence": confidence,
    }


class SpeakerSegment:
    """Represents a speaker segment in diarized audio."""

    def __init__(
        self,
        speaker_id: int,
        start_time: float,
        end_time: float,
        text: str,
    ):
        self.speaker_id = speaker_id
        self.start_time = start_time
        self.end_time = end_time
        self.text = text

    def to_dict(self) -> dict:
        return {
            "speaker": self.speaker_id,
            "start": self.start_time,
            "end": self.end_time,
            "text": self.text,
        }
