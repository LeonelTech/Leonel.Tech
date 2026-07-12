"""Cryptographic hashing helpers (ARCH-011, FILE-001/003).

SHA-256 is the mandatory audit hash. SHA-512 and BLAKE3 may be added later
for internal performance, but SHA-256 must remain in the legal/audit report.
Hashing is streamed so arbitrarily large media never load fully into memory.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

DEFAULT_CHUNK = 1024 * 1024  # 1 MiB
SUPPORTED_ALGORITHMS = ("sha256", "sha512")


@dataclass(frozen=True)
class HashResult:
    algorithm: str
    hexdigest: str
    size_bytes: int


def hash_stream(
    stream: BinaryIO, *, algorithm: str = "sha256", chunk: int = DEFAULT_CHUNK
) -> HashResult:
    """Hash a binary stream, returning digest and byte count."""
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"unsupported hash algorithm: {algorithm!r}")
    hasher = hashlib.new(algorithm)
    size = 0
    while True:
        block = stream.read(chunk)
        if not block:
            break
        size += len(block)
        hasher.update(block)
    return HashResult(algorithm=algorithm, hexdigest=hasher.hexdigest(), size_bytes=size)


def hash_file(
    path: str | Path, *, algorithm: str = "sha256", chunk: int = DEFAULT_CHUNK
) -> HashResult:
    """Hash a file on disk without modifying it (read-only, FILE-001)."""
    with open(path, "rb") as handle:
        return hash_stream(handle, algorithm=algorithm, chunk=chunk)


def hash_bytes(data: bytes, *, algorithm: str = "sha256") -> HashResult:
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"unsupported hash algorithm: {algorithm!r}")
    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return HashResult(algorithm=algorithm, hexdigest=hasher.hexdigest(), size_bytes=len(data))
