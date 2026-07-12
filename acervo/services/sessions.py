"""Cataloging-session orchestration (sections 5 & 7).

Ties the preservation pipeline together: create a collection, register source
media, open a resumable session, then run the preservation pass:

    inventory -> persist DISCOVERED -> per file:
      hash source -> dedup check -> copy+verify -> COPY_VALIDATED (checkpoint)

Re-running a session skips files already validated (JOB-006) and resumes from
the last durable checkpoint (JOB-003). Per-file commits make interruption safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from acervo import __version__
from acervo.config import get_settings
from acervo.db.base import session_scope
from acervo.db.identifiers import next_identifier
from acervo.db.models import (
    CatalogingSession,
    Collection,
    File,
    FileHash,
    SourceMedia,
)
from acervo.domain.identifiers import IdKind
from acervo.domain.paths import assert_destination_outside_source, sanitize_filename
from acervo.domain.states import FileState, assert_transition
from acervo.services import dedup
from acervo.services.audit import record_event
from acervo.services.inventory import walk_source
from acervo.services.preservation import copy_and_verify

# For the preservation MVP, COPY_VALIDATED is the durable success checkpoint;
# content-analysis stages belong to later phases.
PRESERVATION_TERMINAL = FileState.COPY_VALIDATED

_ACTIVE_SUCCESS = {FileState.COPY_VALIDATED, FileState.COMPLETED}
_TERMINAL_FAIL = {FileState.QUARANTINED, FileState.CANCELED}


# --------------------------------------------------------------------------- #
# Setup helpers
# --------------------------------------------------------------------------- #
def create_collection(session: Session, name: str, description: str | None = None) -> Collection:
    ident = next_identifier(session, IdKind.COLLECTION)
    collection = Collection(identifier=ident, name=name, description=description)
    session.add(collection)
    session.flush()
    record_event(
        session,
        action="collection.created",
        subject_type="collection",
        subject_identifier=ident,
        detail={"name": name},
    )
    return collection


def register_source_media(
    session: Session, collection: Collection, label: str, source_root: str
) -> SourceMedia:
    ident = next_identifier(session, IdKind.SOURCE_MEDIA)
    media = SourceMedia(
        identifier=ident,
        collection_id=collection.id,
        label=label,
        source_root=source_root,
    )
    session.add(media)
    session.flush()
    record_event(
        session,
        action="source_media.registered",
        subject_type="source_media",
        subject_identifier=ident,
        detail={"label": label, "source_root": source_root},
    )
    return media


def start_session(
    session: Session,
    collection: Collection,
    media: SourceMedia,
    *,
    source_root: str,
    destination_root: str,
    profile: str = "preservation_only",
) -> CatalogingSession:
    # Section 5 / FILE-007: destination must never be inside the source tree.
    assert_destination_outside_source(source_root, destination_root)
    ident = next_identifier(session, IdKind.CATALOGING_SESSION)
    cat = CatalogingSession(
        identifier=ident,
        collection_id=collection.id,
        source_media_id=media.id,
        source_root=source_root,
        destination_root=destination_root,
        profile=profile,
        software_version=__version__,
        status="running",
    )
    session.add(cat)
    session.flush()
    record_event(
        session,
        action="session.started",
        subject_type="cataloging_session",
        subject_identifier=ident,
        session_identifier=ident,
        detail={"source_root": source_root, "destination_root": destination_root},
    )
    return cat


# --------------------------------------------------------------------------- #
# Preservation run
# --------------------------------------------------------------------------- #
@dataclass
class PreservationStats:
    discovered: int = 0
    already_done: int = 0
    validated: int = 0
    duplicates: int = 0
    quarantined: int = 0
    bytes_validated: int = 0
    errors: list[str] = field(default_factory=list)


def _transition(session: Session, file: File, target: FileState) -> None:
    assert_transition(FileState(file.state), target)
    file.state = target.value


def _master_path(destination_root: str, file: File) -> str:
    from pathlib import Path

    safe_name = sanitize_filename(file.original_filename)
    return str(
        Path(destination_root)
        / "16_VALIDATED_MASTER_FILES"
        / file.identifier
        / safe_name
    )


def _discover(cat_session_id: int) -> int:
    """Persist DISCOVERED rows for any not-yet-seen source path (JOB-002)."""
    new_rows = 0
    with session_scope() as session:
        cat = session.get(CatalogingSession, cat_session_id)
        assert cat is not None
        existing = set(
            session.execute(
                select(File.source_path).where(File.session_id == cat.id)
            ).scalars()
        )
        for item in walk_source(cat.source_root):
            if item.source_path in existing:
                continue
            ident = next_identifier(session, IdKind.FILE)
            file = File(
                identifier=ident,
                collection_id=cat.collection_id,
                source_media_id=cat.source_media_id,
                session_id=cat.id,
                original_filename=item.original_filename,
                display_filename=sanitize_filename(item.original_filename),
                source_path=item.source_path,
                size_bytes=item.size_bytes,
                mime_type=item.mime_type,
                fs_modified_at=item.fs_modified_at,
                state=FileState.DISCOVERED.value,
            )
            if item.read_error:
                file.quarantine_reason = item.read_error
            session.add(file)
            session.flush()
            existing.add(item.source_path)
            new_rows += 1
    return new_rows


def _process_one(session: Session, cat: CatalogingSession, file: File, stats: PreservationStats) -> None:
    settings = get_settings()

    # Inventory-time read error -> quarantine straight away (ERR-001).
    if file.quarantine_reason and FileState(file.state) == FileState.DISCOVERED:
        _transition(session, file, FileState.QUARANTINED)
        stats.quarantined += 1
        record_event(
            session,
            action="file.quarantined",
            subject_type="file",
            subject_identifier=file.identifier,
            session_identifier=cat.identifier,
            detail={"reason": file.quarantine_reason},
        )
        return

    _transition(session, file, FileState.QUEUED)

    # Hash the source (read-only) — primary dedup + audit key.
    try:
        src_result = copy_source_hash(file.source_path, settings.primary_hash)
    except OSError as exc:
        _transition(session, file, FileState.READ_FAILED)
        file.quarantine_reason = str(exc)
        _transition(session, file, FileState.QUARANTINED)
        stats.quarantined += 1
        stats.errors.append(f"{file.identifier}: read failed: {exc}")
        return

    _transition(session, file, FileState.SOURCE_HASHED)
    file.content_sha256 = src_result
    session.add(FileHash(file_id=file.id, algorithm="sha256", hexdigest=src_result, location="source"))

    # Deduplication by content hash (JOB-004/005): link, do not recopy.
    existing = dedup.find_existing_by_hash(
        session, cat.collection_id, src_result, exclude_file_id=file.id
    )
    if existing is not None:
        file.duplicate_of_id = existing.id
        file.validated_master_path = existing.validated_master_path
        # Duplicates skip copy but still complete their preservation lifecycle.
        for target in (
            FileState.COPYING,
            FileState.COPY_VALIDATED,
        ):
            _transition(session, file, target)
        stats.duplicates += 1
        record_event(
            session,
            action="file.duplicate_linked",
            subject_type="file",
            subject_identifier=file.identifier,
            session_identifier=cat.identifier,
            detail={"duplicate_of": existing.identifier, "sha256": src_result},
        )
        _checkpoint(session, cat, file)
        return

    # Copy to validated master and verify by hash (FILE-002/003/004).
    _transition(session, file, FileState.COPYING)
    dest = _master_path(cat.destination_root, file)
    result = copy_and_verify(
        file.source_path,
        dest,
        algorithm="sha256",
        chunk=settings.copy_chunk_bytes,
        max_attempts=settings.copy_max_attempts,
    )
    if not result.validated:
        _transition(session, file, FileState.HASH_MISMATCH)
        file.quarantine_reason = result.error or "hash mismatch"
        _transition(session, file, FileState.QUARANTINED)
        stats.quarantined += 1
        stats.errors.append(f"{file.identifier}: {file.quarantine_reason}")
        record_event(
            session,
            action="file.copy_failed",
            subject_type="file",
            subject_identifier=file.identifier,
            session_identifier=cat.identifier,
            detail={"reason": file.quarantine_reason, "attempts": result.attempts},
        )
        return

    file.validated_master_path = result.dest_path
    session.add(
        FileHash(file_id=file.id, algorithm="sha256", hexdigest=result.dest_hash, location="master")
    )
    _transition(session, file, FileState.COPY_VALIDATED)
    stats.validated += 1
    stats.bytes_validated += result.size_bytes
    record_event(
        session,
        action="file.copy_validated",
        subject_type="file",
        subject_identifier=file.identifier,
        session_identifier=cat.identifier,
        detail={"sha256": result.source_hash, "size_bytes": result.size_bytes},
    )
    _checkpoint(session, cat, file)


def _checkpoint(session: Session, cat: CatalogingSession, file: File) -> None:
    cat.last_checkpoint_file = file.identifier
    cat.last_checkpoint_state = file.state


def copy_source_hash(path: str, algorithm: str) -> str:
    from acervo.domain.hashing import hash_file

    return hash_file(path, algorithm="sha256").hexdigest


def run_preservation(cat_session_id: int) -> PreservationStats:
    """Run (or resume) the preservation pass for a session.

    Idempotent: files already validated or terminally failed are skipped, so a
    second call after interruption only processes remaining work (JOB-003/006).
    """
    stats = PreservationStats()
    stats.discovered = _discover(cat_session_id)

    # Load the set of files still needing work, then process each in its own
    # committed transaction so a crash loses at most one file's progress.
    with session_scope() as session:
        cat = session.get(CatalogingSession, cat_session_id)
        assert cat is not None
        pending_ids = list(
            session.execute(
                select(File.id)
                .where(File.session_id == cat.id)
                .order_by(File.id.asc())
            ).scalars()
        )

    for file_id in pending_ids:
        with session_scope() as session:
            cat = session.get(CatalogingSession, cat_session_id)
            file = session.get(File, file_id)
            assert cat is not None and file is not None
            state = FileState(file.state)
            if state in _ACTIVE_SUCCESS:
                stats.already_done += 1
                continue
            if state in _TERMINAL_FAIL:
                continue
            _process_one(session, cat, file, stats)

    with session_scope() as session:
        cat = session.get(CatalogingSession, cat_session_id)
        assert cat is not None
        cat.status = "completed"
        cat.finished_at = datetime.now(timezone.utc)
        record_event(
            session,
            action="session.preservation_completed",
            subject_type="cataloging_session",
            subject_identifier=cat.identifier,
            session_identifier=cat.identifier,
            detail={
                "validated": stats.validated,
                "duplicates": stats.duplicates,
                "quarantined": stats.quarantined,
            },
        )
    return stats
