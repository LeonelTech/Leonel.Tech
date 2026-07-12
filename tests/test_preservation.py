"""Tests for the copy-and-verify preservation primitive (FILE-002/003/004)."""

from __future__ import annotations

from pathlib import Path

from acervo.domain.hashing import hash_file
from acervo.services.preservation import copy_and_verify


def test_copy_and_verify_success(tmp_path: Path):
    src = tmp_path / "src.bin"
    src.write_bytes(b"legal evidence payload" * 1000)
    dest = tmp_path / "out" / "master.bin"

    result = copy_and_verify(src, dest)

    assert result.validated is True
    assert result.dest_path == str(dest)
    assert dest.exists()
    # source untouched, and hashes match end to end
    assert hash_file(src).hexdigest == hash_file(dest).hexdigest == result.source_hash
    # no leftover partial file
    assert not (tmp_path / "out" / "master.bin.partial").exists()


def test_copy_and_verify_detects_corruption(tmp_path: Path, monkeypatch):
    """If the written copy does not match the source, it must not validate."""
    src = tmp_path / "src.bin"
    src.write_bytes(b"original bytes")
    dest = tmp_path / "master.bin"

    # Simulate a faulty medium: every written copy is silently corrupted.
    import acervo.services.preservation as pres

    real_stream_copy = pres._stream_copy

    def corrupt_copy(source, dest_tmp, chunk):
        real_stream_copy(source, dest_tmp, chunk)
        dest_tmp.write_bytes(b"corrupted")

    monkeypatch.setattr(pres, "_stream_copy", corrupt_copy)

    result = copy_and_verify(src, dest, max_attempts=2)

    assert result.validated is False
    assert result.error is not None
    assert not dest.exists()  # never promote a mismatched copy
    assert not dest.with_name(dest.name + ".partial").exists()
