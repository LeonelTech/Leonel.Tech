"""Non-destructive source inventory (section 5, FILE-006).

Walks a source tree read-only, never following symlinks out of the tree and
never writing anything to the source. Read errors on individual entries are
captured as records rather than aborting the walk.
"""

from __future__ import annotations

import mimetypes
import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class InventoryItem:
    source_path: str
    original_filename: str
    size_bytes: int | None
    mime_type: str | None
    fs_modified_at: datetime | None
    read_error: str | None = None


def _guess_mime(path: Path) -> str | None:
    mime, _ = mimetypes.guess_type(path.name)
    return mime


def walk_source(root: str | Path) -> Iterator[InventoryItem]:
    """Yield one :class:`InventoryItem` per regular file under ``root``.

    Symlinks are not followed (FILE-006). Unreadable entries yield an item with
    ``read_error`` set so the session can quarantine rather than crash (ERR-001).
    """
    root_path = Path(root)
    for dirpath, dirnames, filenames in os.walk(root_path, followlinks=False):
        # Do not descend into symlinked directories.
        dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]
        for name in filenames:
            full = Path(dirpath) / name
            if full.is_symlink():
                yield InventoryItem(
                    source_path=str(full),
                    original_filename=name,
                    size_bytes=None,
                    mime_type=None,
                    fs_modified_at=None,
                    read_error="symlink skipped (not followed)",
                )
                continue
            try:
                stat = full.stat()
                yield InventoryItem(
                    source_path=str(full),
                    original_filename=name,
                    size_bytes=stat.st_size,
                    mime_type=_guess_mime(full),
                    fs_modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                )
            except OSError as exc:
                yield InventoryItem(
                    source_path=str(full),
                    original_filename=name,
                    size_bytes=None,
                    mime_type=None,
                    fs_modified_at=None,
                    read_error=str(exc),
                )


@dataclass(frozen=True)
class InventorySummary:
    total_files: int
    total_bytes: int
    unreadable: int


def summarize(items: list[InventoryItem]) -> InventorySummary:
    total_bytes = sum(i.size_bytes or 0 for i in items)
    unreadable = sum(1 for i in items if i.read_error)
    return InventorySummary(
        total_files=len(items), total_bytes=total_bytes, unreadable=unreadable
    )
