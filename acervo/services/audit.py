"""Audit logging helper (ARCH-012, SEC-005/007)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from acervo.db.models import AuditEvent


def record_event(
    session: Session,
    *,
    action: str,
    actor: str = "system",
    subject_type: str | None = None,
    subject_identifier: str | None = None,
    session_identifier: str | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditEvent:
    """Append an immutable audit event. Never store secrets or file contents."""
    event = AuditEvent(
        action=action,
        actor=actor,
        subject_type=subject_type,
        subject_identifier=subject_identifier,
        session_identifier=session_identifier,
        detail_json=json.dumps(detail, ensure_ascii=False, sort_keys=True)
        if detail is not None
        else None,
    )
    session.add(event)
    return event
