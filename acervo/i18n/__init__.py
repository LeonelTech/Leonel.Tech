"""Localization loader (I18N-001..007).

User-facing strings live in locale JSON files (pt-BR default, en-US secondary).
Source code, identifiers and API contracts stay in English (I18N-003).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_LOCALES_DIR = Path(__file__).parent / "locales"
DEFAULT_LOCALE = "pt-BR"
AVAILABLE_LOCALES = ("pt-BR", "en-US")


@lru_cache(maxsize=None)
def load_locale(locale: str) -> dict[str, str]:
    if locale not in AVAILABLE_LOCALES:
        locale = DEFAULT_LOCALE
    path = _LOCALES_DIR / f"{locale}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def t(key: str, locale: str = DEFAULT_LOCALE, **params: object) -> str:
    """Translate ``key`` for ``locale`` with ICU-style ``{name}`` interpolation.

    Falls back to the default locale, then to the key itself, so a missing
    translation is visible rather than crashing the UI (I18N-002).
    """
    messages = load_locale(locale)
    template = messages.get(key)
    if template is None and locale != DEFAULT_LOCALE:
        template = load_locale(DEFAULT_LOCALE).get(key)
    if template is None:
        return key
    try:
        return template.format(**params) if params else template
    except (KeyError, IndexError):
        return template
