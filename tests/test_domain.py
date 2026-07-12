"""Unit tests for pure domain logic (identifiers, hashing, states, paths)."""

from __future__ import annotations

import io

import pytest

from acervo.domain.hashing import hash_bytes, hash_file, hash_stream
from acervo.domain.identifiers import (
    IdKind,
    format_identifier,
    is_valid_identifier,
    parse_identifier,
)
from acervo.domain.paths import (
    PathSafetyError,
    assert_destination_outside_source,
    deterministic_collision_name,
    is_within,
    sanitize_filename,
)
from acervo.domain.states import (
    FileState,
    InvalidTransition,
    assert_transition,
    can_transition,
    is_terminal,
    reached_checkpoint,
)


# --- identifiers ---
def test_identifier_roundtrip():
    ident = format_identifier(IdKind.COLLECTION, 2026, 3)
    assert ident == "COL-2026-000003"
    kind, year, seq = parse_identifier(ident)
    assert (kind, year, seq) == (IdKind.COLLECTION, 2026, 3)


def test_identifier_validation():
    assert is_valid_identifier("PER-2026-000001")
    assert not is_valid_identifier("PER-26-1")
    assert not is_valid_identifier("XXX-2026-000001")
    with pytest.raises(ValueError):
        format_identifier(IdKind.FILE, 2026, 10**6)


# --- hashing ---
def test_hash_known_vector():
    # SHA-256 of "abc"
    assert (
        hash_bytes(b"abc").hexdigest
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_hash_stream_and_file_agree(tmp_path):
    data = b"x" * (1024 * 5 + 7)
    p = tmp_path / "f.bin"
    p.write_bytes(data)
    assert hash_file(p).hexdigest == hash_stream(io.BytesIO(data)).hexdigest
    assert hash_file(p).size_bytes == len(data)


def test_unsupported_algorithm():
    with pytest.raises(ValueError):
        hash_bytes(b"x", algorithm="md5")


# --- state machine ---
def test_happy_path_transitions():
    assert can_transition(FileState.DISCOVERED, FileState.QUEUED)
    assert can_transition(FileState.COPYING, FileState.COPY_VALIDATED)
    assert not can_transition(FileState.DISCOVERED, FileState.COMPLETED)


def test_invalid_transition_raises():
    with pytest.raises(InvalidTransition):
        assert_transition(FileState.COMPLETED, FileState.QUEUED)


def test_preservation_can_fail_into_quarantine():
    assert can_transition(FileState.COPYING, FileState.HASH_MISMATCH)
    assert can_transition(FileState.HASH_MISMATCH, FileState.QUARANTINED)
    assert is_terminal(FileState.QUARANTINED)
    assert is_terminal(FileState.COMPLETED)


def test_reached_checkpoint():
    assert reached_checkpoint(FileState.COPY_VALIDATED, FileState.SOURCE_HASHED)
    assert not reached_checkpoint(FileState.QUEUED, FileState.COPY_VALIDATED)
    assert not reached_checkpoint(FileState.QUARANTINED, FileState.QUEUED)


# --- paths ---
def test_destination_inside_source_rejected(tmp_path):
    src = tmp_path / "src"
    (src / "inner").mkdir(parents=True)
    with pytest.raises(PathSafetyError):
        assert_destination_outside_source(src, src / "inner")
    with pytest.raises(PathSafetyError):
        assert_destination_outside_source(src, src)


def test_disjoint_destination_ok(tmp_path):
    assert_destination_outside_source(tmp_path / "src", tmp_path / "dst")


def test_is_within(tmp_path):
    assert is_within(tmp_path / "a" / "b", tmp_path)
    assert not is_within(tmp_path, tmp_path / "a")


def test_sanitize_filename():
    assert sanitize_filename('a/b:c*.txt') == "a_b_c_.txt"
    assert sanitize_filename("   ") == "unnamed"
    assert sanitize_filename("CON.txt").startswith("_")


def test_collision_naming():
    assert deterministic_collision_name("report.pdf", 0) == "report.pdf"
    assert deterministic_collision_name("report.pdf", 2) == "report (2).pdf"
