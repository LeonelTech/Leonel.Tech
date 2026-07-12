"""Database-backed identifier allocation (atomic per kind/year)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from acervo.db.models import IdentifierSequence
from acervo.domain.identifiers import IdKind, format_identifier


def next_identifier(session: Session, kind: IdKind, *, year: int | None = None) -> str:
    """Allocate the next identifier for ``kind`` within ``year``.

    Uses a row lock (``with_for_update``) so concurrent sessions never collide.
    The caller's transaction owns the increment; commit persists it.
    """
    if year is None:
        year = datetime.now(timezone.utc).year

    stmt = (
        select(IdentifierSequence)
        .where(IdentifierSequence.kind == kind.value, IdentifierSequence.year == year)
        .with_for_update()
    )
    row = session.execute(stmt).scalar_one_or_none()
    if row is None:
        row = IdentifierSequence(kind=kind.value, year=year, last_value=0)
        session.add(row)
        session.flush()
    row.last_value += 1
    session.flush()
    return format_identifier(kind, year, row.last_value)
