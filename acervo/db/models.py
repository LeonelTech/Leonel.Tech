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
