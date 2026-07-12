"""End-to-end preservation-session tests covering key acceptance criteria."""

from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import func, select

from acervo.db.base import session_scope
from acervo.db.models import AuditEvent, CatalogingSession, File
from acervo.domain.states import FileState
from acervo.services import sessions as svc
from acervo.services.manifest import build_manifest_dict, write_manifest


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bootstrap(source: Path, dest: Path):
    with session_scope() as session:
        col = svc.create_collection(session, "Test Collection")
        media = svc.register_source_media(session, col, "USB-1", str(source))
        cat = svc.start_session(
            session, col, media, source_root=str(source), destination_root=str(dest)
        )
        return cat.id, cat.identifier


def test_full_session_validates_and_dedups(sample_source: Path, tmp_path: Path):
    dest = tmp_path / "repository"
    cat_id, cat_ident = _bootstrap(sample_source, dest)

    stats = svc.run_preservation(cat_id)

    # 3 files discovered; 2 unique validated; 1 exact-hash duplicate (ACC-003).
    assert stats.discovered == 3
    assert stats.validated == 2
    assert stats.duplicates == 1
    assert stats.quarantined == 0

    with session_scope() as session:
        files = session.execute(select(File)).scalars().all()
        by_id = {f.id: f for f in files}
        # Master copies exist and originals are unchanged for canonical files.
        for f in files:
            if f.duplicate_of_id is None:
                assert Path(f.validated_master_path).exists()
                assert Path(f.source_path).exists()
                assert f.state == FileState.COPY_VALIDATED.value

        # The two identical files ("hello world") resolve to exactly one
        # canonical + one duplicate, regardless of filesystem walk order.
        identical = [f for f in files if f.content_sha256 == _sha256_text("hello world")]
        assert len(identical) == 2
        duplicates = [f for f in identical if f.duplicate_of_id is not None]
        assert len(duplicates) == 1
        dup = duplicates[0]
        # The duplicate points back at its identical, canonical sibling.
        canonical = by_id[dup.duplicate_of_id]
        assert canonical.duplicate_of_id is None
        assert canonical.content_sha256 == dup.content_sha256


def test_no_reprocessing_on_rerun(sample_source: Path, tmp_path: Path):
    """Re-running a completed session must not redo validated work (JOB-006)."""
    dest = tmp_path / "repo"
    cat_id, _ = _bootstrap(sample_source, dest)
    svc.run_preservation(cat_id)

    stats2 = svc.run_preservation(cat_id)
    assert stats2.discovered == 0  # nothing new discovered
    assert stats2.validated == 0  # nothing re-copied
    assert stats2.already_done >= 2


def test_resume_after_new_files_added(sample_source: Path, tmp_path: Path):
    """Adding files and re-running resumes without touching completed items."""
    dest = tmp_path / "repo"
    cat_id, _ = _bootstrap(sample_source, dest)
    svc.run_preservation(cat_id)

    (sample_source / "docs" / "c.txt").write_text("brand new file", encoding="utf-8")
    stats = svc.run_preservation(cat_id)
    assert stats.discovered == 1
    assert stats.validated == 1
    assert stats.already_done >= 2


def test_manifest_written_and_self_hashed(sample_source: Path, tmp_path: Path):
    dest = tmp_path / "repo"
    cat_id, cat_ident = _bootstrap(sample_source, dest)
    svc.run_preservation(cat_id)

    with session_scope() as session:
        cat = session.execute(
            select(CatalogingSession).where(CatalogingSession.identifier == cat_ident)
        ).scalar_one()
        manifest = build_manifest_dict(session, cat)
        artifacts = write_manifest(session, cat, dest / "00_COLLECTION_CONTROL")

    assert manifest["file_count"] == 3
    assert artifacts.json_path.exists()
    assert artifacts.csv_path.exists()
    # Recompute the manifest hash and confirm the recorded value matches.
    recomputed = hashlib.sha256(artifacts.json_path.read_bytes()).hexdigest()
    assert recomputed == artifacts.manifest_sha256


def test_audit_trail_records_key_events(sample_source: Path, tmp_path: Path):
    dest = tmp_path / "repo"
    cat_id, cat_ident = _bootstrap(sample_source, dest)
    svc.run_preservation(cat_id)

    with session_scope() as session:
        actions = set(
            session.execute(select(AuditEvent.action)).scalars().all()
        )
    assert {"collection.created", "session.started", "file.copy_validated"} <= actions


def test_original_files_never_modified(sample_source: Path, tmp_path: Path):
    """ACC/Prohibited #1: source hashes before and after must be identical."""
    before = {
        p: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sample_source.rglob("*")
        if p.is_file()
    }
    dest = tmp_path / "repo"
    cat_id, _ = _bootstrap(sample_source, dest)
    svc.run_preservation(cat_id)
    after = {
        p: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sample_source.rglob("*")
        if p.is_file()
    }
    assert before == after
