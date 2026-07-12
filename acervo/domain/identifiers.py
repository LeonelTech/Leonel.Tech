"""Stable, language-neutral identifiers (section 32, NAME-001).

Identifiers follow ``PREFIX-YYYY-NNNNNN`` and are immutable once assigned.
Display names may change; identifiers never do.
"""

from __future__ import annotations

import re
from enum import Enum

_SEQ_WIDTH = 6
_ID_RE = re.compile(r"^(?P<prefix>[A-Z]+)-(?P<year>\d{4})-(?P<seq>\d{6})$")


class IdKind(str, Enum):
    """Every entity/artifact family that receives an identifier."""

    COLLECTION = "COL"
    SOURCE_MEDIA = "MED"
    CATALOGING_SESSION = "CAT"
    FILE = "FIL"
    DOCUMENT = "DOC"
    AUDIO = "AUD"
    VIDEO = "VID"
    IMAGE = "IMG"
    SCREENSHOT = "SCR"
    PERSON = "PER"
    LAWYER = "LAW"
    LAW_FIRM = "FIRM"
    ORGANIZATION = "ORG"
    JUDICIAL_PROCEEDING = "CASE"
    POLICE_ADMIN_RECORD = "PR"
    LOCATION = "LOC"
    DEVICE = "DEV"
    EVENT = "EVT"
    API_REQUEST = "API"
    REPORT = "REP"


def format_identifier(kind: IdKind, year: int, sequence: int) -> str:
    """Build an identifier string, e.g. ``COL-2026-000003``."""
    if sequence < 0:
        raise ValueError("sequence must be non-negative")
    if sequence >= 10**_SEQ_WIDTH:
        raise ValueError(f"sequence {sequence} exceeds {_SEQ_WIDTH} digits")
    if not (1 <= year <= 9999):
        raise ValueError("year out of range")
    return f"{kind.value}-{year:04d}-{sequence:0{_SEQ_WIDTH}d}"


def parse_identifier(identifier: str) -> tuple[IdKind, int, int]:
    """Inverse of :func:`format_identifier`. Raises ``ValueError`` if malformed."""
    match = _ID_RE.match(identifier)
    if not match:
        raise ValueError(f"malformed identifier: {identifier!r}")
    prefix = match.group("prefix")
    try:
        kind = IdKind(prefix)
    except ValueError as exc:
        raise ValueError(f"unknown identifier prefix: {prefix!r}") from exc
    return kind, int(match.group("year")), int(match.group("seq"))


def is_valid_identifier(identifier: str) -> bool:
    try:
        parse_identifier(identifier)
        return True
    except ValueError:
        return False
