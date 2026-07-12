# Acervo

**Local-first legal, evidentiary and investigative cataloging platform**
Plataforma local de catalogação jurídica, probatória e investigativa

> Runtime language: Portuguese (Brazil) by default, English optional.
> Source code, identifiers and API contracts are kept in English by design.

Acervo inventories, hash-validates, copies, and organizes large collections of
legal and investigative files **without ever modifying the client's originals**.
Every extracted fact is meant to link back to its exact source, uncertainty is
made visible, and no automated result is presented as a legal conclusion.

This repository currently implements **Phase 1 (Foundation)** and the core of
**Phase 2 (Preservation)** from the master development specification — the parts
that must be rock-solid before any OCR, transcription or AI analysis is added.

---

## What works today (MVP core)

- 🗂️ **Research Collections** (Acervo de Pesquisa) with stable, language-neutral
  identifiers (`COL-YYYY-NNNNNN`, `FIL-YYYY-NNNNNN`, …).
- 🔍 **Non-destructive inventory** of a source folder/device (read-only; symlinks
  and unreadable files handled without crashing the session).
- 🔐 **SHA-256 verified copying**: streamed copy → hash → atomic promotion. A
  hash mismatch is **never** silently accepted — it is quarantined and retried.
- ♻️ **Hash-based deduplication**: identical content under a different name is
  detected and linked, not re-copied. Same name / different content stays
  distinct.
- ⏯️ **Resumable sessions**: re-running never repeats completed work; new files
  are picked up from the last durable checkpoint.
- 🧾 **Auditable manifest** (JSON + CSV) that is itself SHA-256 hashed, plus an
  append-only audit-event trail.
- 🌐 **Loopback-only local API** (FastAPI) + a minimal accessible web shell with
  a pt-BR / en-US language selector.

## What is intentionally *not* here yet

OCR, transcription/diarization, entity & dossier extraction, integrity analysis,
external-AI fallback, roles/encryption and the Windows installer are **later
phases**, tracked with acceptance criteria in [`docs/BACKLOG.md`](docs/BACKLOG.md).
Nothing was silently dropped.

---

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run a preservation session from the terminal
python -m acervo.cli preserve \
  --collection "Caso Silva" \
  --source /path/to/client_drive \
  --destination /path/to/repository

# Or launch the local web app (binds to 127.0.0.1 only)
python -m acervo.cli serve   # then open http://127.0.0.1:8787
```

Run the tests:

```bash
python -m pytest
```

Configuration is via `ACERVO_`-prefixed environment variables (see
`acervo/config.py`); by default data lives in `~/.acervo/`.

## Documentation

| Document | Contents |
|----------|----------|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Stack, layering, storage model, decisions |
| [`docs/STATE_MACHINE.md`](docs/STATE_MACHINE.md) | File cataloging states & transitions |
| [`docs/ACCEPTANCE_TESTS.md`](docs/ACCEPTANCE_TESTS.md) | Preservation acceptance criteria ↔ tests |
| [`docs/BACKLOG.md`](docs/BACKLOG.md) | Deferred features by phase, with acceptance criteria |

## Safety principles (non-negotiable)

- Client originals are **read-only** — never renamed, edited, deleted, or given
  sidecar files.
- Timestamps and filenames are **never** treated as authenticated truth.
- Duplicate people/entities are **never** merged by name similarity alone.
- Preliminary technical indicators are **never** presented as forensic
  conclusions.
- No data leaves the machine without explicit, auditable authorization.
