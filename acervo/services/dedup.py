"""Content-hash deduplication (JOB-004/005/006).

The content hash is the primary dedup key; path, name, size and timestamps are
only supporting attributes. A previously cataloged hash is never reprocessed by
default — the caller decides how to associate the duplicate.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from acervo.db.models import File


def find_existing_by_hash(
    session: Session, collection_id: int, sha256: str, *, exclude_file_id: int | None = None
) -> File | None:
    """Return the first non-duplicate file in the collection with this hash."""
    stmt = (
        select(File)
        .where(
            File.collection_id == collection_id,
            File.content_sha256 == sha256,
            File.duplicate_of_id.is_(None),
        )
        .order_by(File.id.asc())
    )
    if exclude_file_id is not None:
        stmt = stmt.where(File.id != exclude_file_id)
    return session.execute(stmt).scalars().first()
