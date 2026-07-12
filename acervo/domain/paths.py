"""Path-safety checks for the preservation pipeline.

Guards enforced here:

* The destination repository must never live inside the source path, and vice
  versa (setup wizard, section 5; FILE-007).
* Extraction / staging must stay within controlled working storage — reject
  path traversal that would escape the repository root (security tests, 27.1).
* Filename collisions are resolved deterministically and recorded (NAME-004).
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path, PurePath


class PathSafetyError(ValueError):
    """Raised when a path would violate a preservation safety rule."""


def _resolve(path: str | Path) -> Path:
    # resolve() normalises ``..`` and symlinks without requiring existence.
    return Path(path).expanduser().resolve()


def is_within(child: str | Path, parent: str | Path) -> bool:
    """True if ``child`` is equal to or nested under ``parent``."""
    child_r = _resolve(child)
    parent_r = _resolve(parent)
    return child_r == parent_r or parent_r in child_r.parents


def assert_destination_outside_source(source: str | Path, destination: str | Path) -> None:
    """Enforce that source and destination are disjoint trees (section 5)."""
    src = _resolve(source)
    dst = _resolve(destination)
    if src == dst:
        raise PathSafetyError("source and destination must not be the same path")
    if is_within(dst, src):
        raise PathSafetyError("destination must not be located inside the source path")
    if is_within(src, dst):
        raise PathSafetyError("source must not be located inside the destination path")


def assert_within_root(candidate: str | Path, root: str | Path) -> None:
    """Reject any candidate path that escapes ``root`` (anti-traversal)."""
    if not is_within(candidate, root):
        raise PathSafetyError(f"path escapes controlled root: {candidate!r}")


_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_WIN = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def sanitize_filename(name: str, *, fallback: str = "unnamed") -> str:
    """Produce a safe *display/export* filename (NAME-002).

    The original filename is always preserved verbatim in the database; this is
    only for generated destination/export names. Never returns an empty string
    or a reserved Windows device name.
    """
    name = unicodedata.normalize("NFC", name).strip()
    name = _UNSAFE_CHARS.sub("_", name)
    name = name.strip(" .")  # Windows dislikes trailing spaces/dots
    if not name:
        return fallback
    stem = PurePath(name).stem.upper()
    if stem in _RESERVED_WIN:
        name = f"_{name}"
    return name[:255]


def deterministic_collision_name(name: str, attempt: int) -> str:
    """Deterministic renaming for filename collisions (NAME-004).

    ``report.pdf`` -> ``report (1).pdf`` -> ``report (2).pdf`` ...
    """
    if attempt <= 0:
        return name
    p = PurePath(name)
    return f"{p.stem} ({attempt}){p.suffix}"
