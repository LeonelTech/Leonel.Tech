"""Verified copy of a client original to a validated master (section 6).

Guarantees:
* The source is opened read-only and never modified (FILE-001, prohibited #1).
* The copy is streamed to a temporary path, hashed, and only promoted to its
  final name via an atomic rename once source and destination hashes match
  (FILE-002/003).
* A hash mismatch never silently succeeds: the partial copy is removed and the
  result is flagged for quarantine and retry (FILE-004).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from acervo.domain.hashing import DEFAULT_CHUNK, hash_file


@dataclass(frozen=True)
class CopyResult:
    validated: bool
    source_hash: str
    dest_hash: str | None
    size_bytes: int
    dest_path: str | None
    attempts: int
    error: str | None = None


def _stream_copy(source: Path, dest_tmp: Path, chunk: int) -> None:
    """Copy bytes source -> dest_tmp, flushing to disk before returning."""
    with open(source, "rb") as src, open(dest_tmp, "wb") as dst:
        while True:
            block = src.read(chunk)
            if not block:
                break
            dst.write(block)
        dst.flush()
        os.fsync(dst.fileno())


def copy_and_verify(
    source_path: str | Path,
    dest_path: str | Path,
    *,
    algorithm: str = "sha256",
    chunk: int = DEFAULT_CHUNK,
    max_attempts: int = 3,
) -> CopyResult:
    """Copy ``source_path`` to ``dest_path`` and verify by hash.

    ``dest_path`` is the final master path; a sibling ``<name>.partial`` file is
    used during the copy and atomically renamed on success. On repeated hash
    mismatch the destination is left absent and ``validated`` is False.
    """
    source = Path(source_path)
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    source_result = hash_file(source, algorithm=algorithm, chunk=chunk)
    tmp = dest.with_name(dest.name + ".partial")

    last_dest_hash: str | None = None
    last_error: str | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            _stream_copy(source, tmp, chunk)
            dest_result = hash_file(tmp, algorithm=algorithm, chunk=chunk)
            last_dest_hash = dest_result.hexdigest
            if dest_result.hexdigest == source_result.hexdigest:
                os.replace(tmp, dest)  # atomic promotion
                return CopyResult(
                    validated=True,
                    source_hash=source_result.hexdigest,
                    dest_hash=dest_result.hexdigest,
                    size_bytes=source_result.size_bytes,
                    dest_path=str(dest),
                    attempts=attempt,
                )
            # Mismatch: discard the partial and retry (FILE-004).
            last_error = "hash mismatch between source and destination copy"
        except OSError as exc:
            last_error = str(exc)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    return CopyResult(
        validated=False,
        source_hash=source_result.hexdigest,
        dest_hash=last_dest_hash,
        size_bytes=source_result.size_bytes,
        dest_path=None,
        attempts=max_attempts,
        error=last_error,
    )
