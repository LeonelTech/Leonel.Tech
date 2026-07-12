"""Application configuration (SEC-002: loopback by default).

Settings are read from environment variables prefixed with ``ACERVO_`` and
from an optional ``.env`` file. Defaults are safe for a single-user portable
edition using SQLite.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> Path:
    return Path.home() / ".acervo"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ACERVO_", env_file=".env", extra="ignore"
    )

    # --- Networking (SEC-002) ---
    host: str = "127.0.0.1"  # loopback only; never bind 0.0.0.0 by default
    port: int = 8787

    # --- Storage ---
    data_dir: Path = Field(default_factory=_default_data_dir)

    # --- Localization (I18N-001) ---
    default_locale: str = "pt-BR"

    # --- Preservation policy ---
    # Primary audit hash (ARCH-011). SHA-256 is mandatory in reports.
    primary_hash: str = "sha256"
    copy_chunk_bytes: int = 1024 * 1024  # 1 MiB streaming copy/hash buffer
    # Retry attempts on a hash mismatch before quarantine (FILE-004).
    copy_max_attempts: int = 3

    @property
    def db_path(self) -> Path:
        return self.data_dir / "acervo.sqlite3"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings_cache() -> None:
    """Test hook: force re-reading settings (e.g. after env changes)."""
    global _settings
    _settings = None
