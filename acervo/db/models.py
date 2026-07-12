"""Core ORM models for the preservation pipeline (subset of section 21).

Design rules honoured here:
* Stable language-neutral identifiers alongside surrogate PKs (NAME-001).
* Original filename preserved verbatim; a separate display name may differ
  (NAME-002).
* Every date is labelled by source rather than trusted blindly (FILE-005).
* Hashes live in their own table so multiple algorithms can coexist (ARCH-011).
* An append-only audit table records preservation-relevant events (ARCH-012).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from acervo.db.base import Base
from acervo.domain.states import FileState


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class IdentifierSequence(Base):
    """Monotonic per-(kind, year) counter backing identifier generation."""

    __tablename__ = "identifier_sequences"
    __table_args__ = (UniqueConstraint("kind", "year", name="uq_idseq_kind_year"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Collection(TimestampMixin, Base):
    """A Research Collection / Acervo de Pesquisa (section 5)."""

    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identifier: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    media: Mapped[list["SourceMedia"]] = relationship(back_populates="collection")
    sessions: Mapped[list["CatalogingSession"]] = relationship(back_populates="collection")
    files: Mapped[list["File"]] = relationship(back_populates="collection")


class SourceMedia(TimestampMixin, Base):
    """A registered source device/folder (section 5, intake)."""

    __tablename__ = "source_media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identifier: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(512), nullable=False)
    source_root: Mapped[str] = mapped_column(Text, nullable=False)
    intake_notes: Mapped[str | None] = mapped_column(Text)
    # Whether the physical media has been returned to the client (ACC-002).
    returned_to_owner: Mapped[bool] = mapped_column(default=False)

    collection: Mapped[Collection] = relationship(back_populates="media")


class CatalogingSession(TimestampMixin, Base):
    """A resumable import/cataloging run with checkpoints (JOB-001)."""

    __tablename__ = "cataloging_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identifier: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), nullable=False)
    source_media_id: Mapped[int] = mapped_column(ForeignKey("source_media.id"), nullable=False)
    source_root: Mapped[str] = mapped_column(Text, nullable=False)
    destination_root: Mapped[str] = mapped_column(Text, nullable=False)
    profile: Mapped[str] = mapped_column(String(64), default="preservation_only")
    software_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Identifier of the last file that reached a durable checkpoint (JOB-007).
    last_checkpoint_file: Mapped[str | None] = mapped_column(String(32))
    last_checkpoint_state: Mapped[str | None] = mapped_column(String(32))

    collection: Mapped[Collection] = relationship(back_populates="sessions")
    files: Mapped[list["File"]] = relationship(back_populates="session")


class File(TimestampMixin, Base):
    """A discovered canonical file and its preservation state (section 6)."""

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identifier: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), nullable=False)
    source_media_id: Mapped[int] = mapped_column(ForeignKey("source_media.id"), nullable=False)
    session_id: Mapped[int] = mapped_column(ForeignKey("cataloging_sessions.id"), nullable=False)

    # NAME-002: original name preserved verbatim; display name may be sanitised.
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    display_filename: Mapped[str | None] = mapped_column(Text)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    validated_master_path: Mapped[str | None] = mapped_column(Text)

    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    mime_type: Mapped[str | None] = mapped_column(String(255))

    # FILE-005: file-system timestamps stored but labelled as such, never trusted
    # as authoritative creation time.
    fs_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    state: Mapped[str] = mapped_column(String(32), default=FileState.DISCOVERED.value)
    # Deduplication key (JOB-004): primary content hash, populated once hashed.
    content_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    # If this file is an exact-hash duplicate, point at the first-seen file.
    duplicate_of_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))
    quarantine_reason: Mapped[str | None] = mapped_column(Text)

    collection: Mapped[Collection] = relationship(back_populates="files")
    session: Mapped[CatalogingSession] = relationship(back_populates="files")
    hashes: Mapped[list["FileHash"]] = relationship(
        back_populates="file", cascade="all, delete-orphan"
    )


class FileHash(Base):
    """One hash value per (file, algorithm, location). (ARCH-011, FILE-003)."""

    __tablename__ = "file_hashes"
    __table_args__ = (
        UniqueConstraint("file_id", "algorithm", "location", name="uq_hash_file_algo_loc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(16), nullable=False)
    hexdigest: Mapped[str] = mapped_column(String(128), nullable=False)
    # "source" (client original) or "master" (validated repository copy).
    location: Mapped[str] = mapped_column(String(16), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    file: Mapped[File] = relationship(back_populates="hashes")


class AuditEvent(Base):
    """Append-only audit trail (ARCH-012, SEC-005). Never updated in place."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(128), default="system")
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    # Loose references so audit rows survive even if a subject row is removed.
    subject_type: Mapped[str | None] = mapped_column(String(64))
    subject_identifier: Mapped[str | None] = mapped_column(String(64))
    session_identifier: Mapped[str | None] = mapped_column(String(32))
    # Structured JSON payload as text (SEC-007: never log file contents/secrets).
    detail_json: Mapped[str | None] = mapped_column(Text)


# --- Phase 4: OCR & Documents ---


class OcrResult(TimestampMixin, Base):
    """OCR extraction from a file (Phase 4)."""

    __tablename__ = "ocr_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False)  # native_pdf, tesseract, …
    method_version: Mapped[str] = mapped_column(String(32))
    model_version: Mapped[str | None] = mapped_column(String(64))
    full_text: Mapped[str | None] = mapped_column(Text)
    quality_score: Mapped[float] = mapped_column(default=0.0)  # 0-100
    duration_seconds: Mapped[float | None] = mapped_column()
    error_message: Mapped[str | None] = mapped_column(Text)


class OcrRegion(Base):
    """Bounding box + text for a detected region (OCR-005)."""

    __tablename__ = "ocr_regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ocr_result_id: Mapped[int] = mapped_column(ForeignKey("ocr_results.id"), nullable=False)
    page: Mapped[int | None] = mapped_column()
    text: Mapped[str] = mapped_column(Text, nullable=False)
    x0: Mapped[float | None] = mapped_column()  # left
    y0: Mapped[float | None] = mapped_column()  # top
    x1: Mapped[float | None] = mapped_column()  # right
    y1: Mapped[float | None] = mapped_column()  # bottom
    confidence: Mapped[str] = mapped_column(String(16), default="medium")  # high/medium/low/illegible
    is_partial: Mapped[bool] = mapped_column(default=False)


class OcrCorrection(TimestampMixin, Base):
    """Human correction of OCR with audit trail (OCR-008)."""

    __tablename__ = "ocr_corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ocr_region_id: Mapped[int] = mapped_column(ForeignKey("ocr_regions.id"), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_text: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_by: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)


# --- Phase 5: Multimedia ---


class TranscriptResult(TimestampMixin, Base):
    """Transcription of audio/video (Phase 5)."""

    __tablename__ = "transcript_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False)  # faster_whisper, …
    method_version: Mapped[str] = mapped_column(String(32))
    model_version: Mapped[str | None] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(16), default="pt-BR")
    duration_seconds: Mapped[float | None] = mapped_column()
    quality_score: Mapped[float] = mapped_column(default=0.0)
    diarization_used: Mapped[bool] = mapped_column(default=False)
    error_message: Mapped[str | None] = mapped_column(Text)


class TranscriptSegment(Base):
    """One segment of a transcript (typically sentence-level, AV-004)."""

    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transcript_id: Mapped[int] = mapped_column(ForeignKey("transcript_results.id"), nullable=False)
    segment_number: Mapped[int] = mapped_column()
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_seconds: Mapped[float] = mapped_column()
    end_seconds: Mapped[float] = mapped_column()
    speaker: Mapped[str] = mapped_column(String(64), default="SPEAKER-000")  # neutral ID
    confidence: Mapped[float] = mapped_column(default=0.5)  # 0-1


class Speaker(Base):
    """A speaker identity mapping (AV-006)."""

    __tablename__ = "speakers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transcript_id: Mapped[int] = mapped_column(ForeignKey("transcript_results.id"), nullable=False)
    speaker_label: Mapped[str] = mapped_column(String(64), nullable=False)  # SPEAKER-000
    reviewed_as: Mapped[str | None] = mapped_column(String(256))  # "John Doe" after review
    reviewed_by: Mapped[str | None] = mapped_column(String(128))
    review_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reference_excerpt: Mapped[str | None] = mapped_column(Text)  # sample for identity confirmation


class Frame(Base):
    """Extracted video frame metadata (AV-007)."""

    __tablename__ = "frames"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), nullable=False)
    frame_number: Mapped[int] = mapped_column()
    timestamp_seconds: Mapped[float] = mapped_column()
    frame_path: Mapped[str | None] = mapped_column(Text)  # path to extracted thumbnail
    width: Mapped[int | None] = mapped_column()
    height: Mapped[int | None] = mapped_column()
    has_scene_change: Mapped[bool] = mapped_column(default=False)
    visual_description: Mapped[str | None] = mapped_column(Text)  # (AV-009)


class VisualDescription(TimestampMixin, Base):
    """Objective visual description of media (AV-009, AV-010)."""

    __tablename__ = "visual_descriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), nullable=False)
    frame_id: Mapped[int | None] = mapped_column(ForeignKey("frames.id"))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(String(32))  # local_vision, external_ai
    quality_score: Mapped[float] = mapped_column(default=0.0)
    limitations: Mapped[str | None] = mapped_column(Text)


# --- Phase 6: Entities, Assertions, Relationships ---


class Entity(TimestampMixin, Base):
    """An entity in the catalog (section 8: person, lawyer, proceeding…)."""

    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identifier: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # person, lawyer, proceeding…
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text)


class Assertion(TimestampMixin, Base):
    """A cataloged fact with full provenance (section 21.1)."""

    __tablename__ = "assertions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    predicate: Mapped[str] = mapped_column(String(64), nullable=False)  # works_at, represents…
    object_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"))
    literal_value: Mapped[str | None] = mapped_column(Text)

    source_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))
    source_page: Mapped[int | None] = mapped_column()
    source_timestamp_start: Mapped[float | None] = mapped_column()
    source_timestamp_end: Mapped[float | None] = mapped_column()

    extraction_method: Mapped[str] = mapped_column(String(32), default="manual")
    confidence: Mapped[str] = mapped_column(String(32), default="unverified")  # enum value
    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    limitations: Mapped[str | None] = mapped_column(Text)


class Relationship(TimestampMixin, Base):
    """Connection between entities (section 8.2-8.4)."""

    __tablename__ = "relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    target_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[str | None] = mapped_column(String(32))  # ISO 8601
    end_date: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[str] = mapped_column(String(32), default="unverified")
    is_confirmed: Mapped[bool] = mapped_column(default=False)


class Chronology(TimestampMixin, Base):
    """Event in master or entity chronology."""

    __tablename__ = "chronology_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"))  # None = master chronology
    event_date: Mapped[str] = mapped_column(String(32), nullable=False)  # ISO 8601 or fuzzy
    event_type: Mapped[str] = mapped_column(String(64))  # filing, judgment, communication…
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))
    confidence: Mapped[str] = mapped_column(String(32), default="unverified")


# --- Phase 8: Integrity & Anomalies ---


class IntegrityFinding(TimestampMixin, Base):
    """Technical indicator warranting review (section 18, INT-001/002)."""

    __tablename__ = "integrity_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), nullable=False)
    anomaly_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="info")  # info, low, medium, high
    tool: Mapped[str] = mapped_column(String(64))  # FFprobe, PDFchecker…
    tool_version: Mapped[str | None] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(default=0.5)  # 0-1
    location: Mapped[str | None] = mapped_column(Text)  # page, timestamp, frame range
    description: Mapped[str] = mapped_column(Text)
    benign_explanations: Mapped[str | None] = mapped_column(Text)  # JSON list
    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    notes: Mapped[str | None] = mapped_column(Text)


class Contradiction(TimestampMixin, Base):
    """Two assertions in conflict, flagged for human review (section 18)."""

    __tablename__ = "contradictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assertion_1_id: Mapped[int] = mapped_column(ForeignKey("assertions.id"), nullable=False)
    assertion_2_id: Mapped[int] = mapped_column(ForeignKey("assertions.id"), nullable=False)
    conflict_type: Mapped[str] = mapped_column(String(64))  # temporal, factual, named_entity
    confidence: Mapped[float] = mapped_column(default=0.5)
    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    notes: Mapped[str | None] = mapped_column(Text)


class Limitation(Base):
    """Quality/completeness limitation of a file analysis (section 26, ERR-003)."""

    __tablename__ = "limitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), nullable=False)
    limitation_type: Mapped[str] = mapped_column(String(64))  # unsupported_content, low_confidence…
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="info")
    suggested_action: Mapped[str | None] = mapped_column(Text)
