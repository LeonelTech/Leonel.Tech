"""Cataloging manifest generation (FILE-008).

Emits a JSON manifest and a CSV index describing every file in a session, then
hashes the JSON manifest itself so the manifest's own integrity is verifiable.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from acervo import __version__
from acervo.db.models import CatalogingSession, File
from acervo.domain.hashing import hash_bytes

_MANIFEST_COLUMNS = [
    "identifier",
    "original_filename",
    "source_path",
    "validated_master_path",
    "size_bytes",
    "mime_type",
    "state",
    "content_sha256",
    "duplicate_of",
]


@dataclass
class ManifestFileRow:
    identifier: str
    original_filename: str
    source_path: str
    validated_master_path: str | None
    size_bytes: int | None
    mime_type: str | None
    state: str
    content_sha256: str | None
    duplicate_of: str | None


def _collect_rows(session: Session, cat_session: CatalogingSession) -> list[ManifestFileRow]:
    files = (
        session.execute(
            select(File).where(File.session_id == cat_session.id).order_by(File.id.asc())
        )
        .scalars()
        .all()
    )
    id_by_pk = {f.id: f.identifier for f in files}
    rows: list[ManifestFileRow] = []
    for f in files:
        rows.append(
            ManifestFileRow(
                identifier=f.identifier,
                original_filename=f.original_filename,
                source_path=f.source_path,
                validated_master_path=f.validated_master_path,
                size_bytes=f.size_bytes,
                mime_type=f.mime_type,
                state=f.state,
                content_sha256=f.content_sha256,
                duplicate_of=id_by_pk.get(f.duplicate_of_id) if f.duplicate_of_id else None,
            )
        )
    return rows


def build_manifest_dict(session: Session, cat_session: CatalogingSession) -> dict:
    rows = _collect_rows(session, cat_session)
    return {
        "manifest_version": 1,
        "software": "Acervo",
        "software_version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "session": {
            "identifier": cat_session.identifier,
            "collection_id": cat_session.collection_id,
            "source_root": cat_session.source_root,
            "destination_root": cat_session.destination_root,
            "profile": cat_session.profile,
            "status": cat_session.status,
        },
        "file_count": len(rows),
        "files": [asdict(r) for r in rows],
    }


def render_csv(session: Session, cat_session: CatalogingSession) -> str:
    rows = _collect_rows(session, cat_session)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_MANIFEST_COLUMNS)
    writer.writeheader()
    for r in rows:
        writer.writerow(asdict(r))
    return buf.getvalue()


@dataclass(frozen=True)
class ManifestArtifacts:
    json_path: Path
    csv_path: Path
    manifest_sha256: str


def write_manifest(
    session: Session, cat_session: CatalogingSession, out_dir: str | Path
) -> ManifestArtifacts:
    """Write ``manifest.json`` + ``manifest.csv`` and hash the JSON manifest."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest_dict(session, cat_session)
    json_bytes = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode(
        "utf-8"
    )
    manifest_hash = hash_bytes(json_bytes).hexdigest

    json_path = out / "manifest.json"
    json_path.write_bytes(json_bytes)
    (out / "manifest.sha256").write_text(f"{manifest_hash}  manifest.json\n", encoding="utf-8")

    csv_path = out / "manifest.csv"
    csv_path.write_text(render_csv(session, cat_session), encoding="utf-8")

    return ManifestArtifacts(
        json_path=json_path, csv_path=csv_path, manifest_sha256=manifest_hash
    )
