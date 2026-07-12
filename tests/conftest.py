"""Shared pytest fixtures: isolate each test in its own temp data dir + DB."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point Acervo at a throwaway data dir and reset cached engine/settings."""
    data_dir = tmp_path / "acervo_data"
    monkeypatch.setenv("ACERVO_DATA_DIR", str(data_dir))

    from acervo import config
    from acervo.db import base

    config.reset_settings_cache()
    base.reset_engine_cache()
    base.init_db()

    yield

    base.reset_engine_cache()
    config.reset_settings_cache()


@pytest.fixture
def sample_source(tmp_path: Path) -> Path:
    """A small source tree with a duplicate and nested files."""
    src = tmp_path / "source"
    (src / "docs").mkdir(parents=True)
    (src / "docs" / "a.txt").write_text("hello world", encoding="utf-8")
    (src / "docs" / "b.txt").write_text("different content", encoding="utf-8")
    # exact-content duplicate of a.txt under a different name/location
    (src / "copy_of_a.txt").write_text("hello world", encoding="utf-8")
    return src
