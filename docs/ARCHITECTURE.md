# Architecture

This is a condensed Architecture Decision Record for the MVP core (Phases 1–2).
It will grow as later phases land.

## Goals driving the design

1. **Original-file safety above all.** The pipeline must be provably incapable
   of modifying client source media.
2. **Auditability & reproducibility.** Every state change and preservation
   action is recorded; the manifest is self-hashed.
3. **Local-first / offline.** Core cataloging never requires network access.
4. **Resumability.** A 20+ GB session can be interrupted and resumed without
   repeating completed work.

## Layering

```
acervo/
├── config.py            # env-driven settings (loopback host, hashing policy)
├── domain/              # pure logic, no I/O — fully unit-testable
│   ├── identifiers.py   #   COL-YYYY-NNNNNN formatting/parsing
│   ├── hashing.py       #   streamed SHA-256 (ARCH-011)
│   ├── states.py        #   file state machine + allowed transitions
│   └── paths.py         #   path-safety, sanitization, collision naming
├── db/                  # persistence
│   ├── base.py          #   engine/session, SQLite (portable) / Postgres-ready
│   ├── models.py        #   ORM: collections, media, sessions, files, hashes, audit
│   └── identifiers.py   #   atomic per-(kind,year) identifier allocation
├── services/            # orchestration (side-effecting)
│   ├── inventory.py     #   non-destructive source walk
│   ├── preservation.py  #   copy + verify + atomic promotion
│   ├── dedup.py         #   content-hash deduplication
│   ├── manifest.py      #   JSON/CSV manifest + self-hash
│   ├── audit.py         #   append-only audit events
│   └── sessions.py      #   the resumable preservation run
├── api/                 # FastAPI routes + Pydantic schemas (loopback only)
├── i18n/                # pt-BR / en-US locale files + loader
├── web/                 # minimal accessible UI shell
├── cli.py               # `acervo serve` / `acervo preserve`
└── main.py              # ASGI app factory
```

The **domain** layer has no framework or database dependencies, so the
safety-critical logic (hashing, transitions, path checks) is tested in
isolation. **Services** compose the domain with persistence and the filesystem.
The **API/CLI/web** layers are thin adapters over services.

## Key decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language / stack | Python 3.11+ (3.12+ recommended), FastAPI, SQLAlchemy 2.x, Pydantic 2 | ARCH-001..005 |
| Database | SQLite for portable single-user; models are Postgres-ready | ARCH-004 |
| Audit hash | SHA-256 (mandatory), streamed | ARCH-011, FILE-003 |
| Copy strategy | stream to `*.partial`, hash, then `os.replace` (atomic) | FILE-002/003 |
| Dedup key | content SHA-256; path/name/size are supporting only | JOB-004 |
| Resumability | per-file committed transactions + happy-path checkpoints | JOB-003/006 |
| Networking | bind `127.0.0.1` by default; OpenAPI docs disabled | SEC-002, ARCH-002 |
| i18n | ICU-style locale JSON; identifiers stay English | I18N-003/004 |
| Migrations | `create_all` for MVP; Alembic in Phase 1 hardening (backlog) | ARCH-005 |

## Preservation flow (Phase 2)

```
source file (read-only)
   → hash source (SHA-256)              → SOURCE_HASHED
   → dedup check by content hash
        ├─ duplicate → link to canonical, no copy
        └─ unique    → stream copy to <dest>/16_VALIDATED_MASTER_FILES/<FIL id>/
                       → hash destination
                       → match?  yes → atomic promote → COPY_VALIDATED (checkpoint)
                                 no  → discard, retry, else QUARANTINED
   → manifest.json + manifest.csv + manifest.sha256
```

`COPY_VALIDATED` is the durable success checkpoint for the preservation MVP;
content-analysis stages (metadata → OCR → transcription → …) extend the same
state machine in later phases without deleting prior work (JOB-006).

## Data model (implemented subset)

`identifier_sequences`, `collections`, `source_media`, `cataloging_sessions`,
`files`, `file_hashes`, `audit_events`. The full domain model (entities,
dossiers, OCR, transcripts, API receipts, etc. — section 21 of the spec) is
introduced per phase; see `docs/BACKLOG.md`.
