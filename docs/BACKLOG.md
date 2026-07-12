# Backlog — deferred features by phase

Per the specification's operating principle, no requirement is silently dropped.
Everything not in the current MVP core is recorded here with its phase and
acceptance criteria. Phases follow the master roadmap (section 28).

## Delivered

- **Phase 1 — Foundation:** project structure, local loopback server, UI shell,
  i18n (pt-BR/en-US), settings, database, core domain modules, tests.
- **Phase 2 — Preservation (core):** source/destination selection with
  path-safety, media intake, non-destructive inventory, SHA-256 hashing,
  verified copy, dedup, manifest (JSON/CSV + self-hash), resumable sessions,
  audit trail.

## Phase 2 — remaining hardening

- [ ] Alembic migrations replacing `create_all` (ARCH-005).
- [ ] Durable job queue with worker processes for parallel copy/hash (ARCH-006).
- [ ] Performance validation at tens of thousands of files / large videos (ACC-001).
- [ ] Return-of-media acknowledgment + preservation-guidance report (ACC-002).
- [ ] Progress reporting stream (discovered/copied/validated/failed) to the UI (JOB-007).
- [ ] Raw metadata capture during intake (`file_metadata_raw`) (section 12).

## Phase 3 — Catalog Core

- [ ] Central catalog table UI with filtering, column chooser, bulk actions.
- [ ] File-detail page (original/master/working/derived tabs).
- [ ] Operational status & relevance values with provenance (section 20).

## Phase 4 — Documents & OCR

- [ ] Native PDF text extraction; OCR adapters (PaddleOCR/Tesseract) behind an
      interface (ARCH-009).
- [ ] Word/line bounding boxes; `[illegible]` markers; human correction trail.
- [ ] CNJ process-number / OAB / CPF-CNPJ detection & validation (LEGAL-001).

## Phase 5 — Multimedia

- [ ] FFmpeg/FFprobe inspection; audio extraction to working copies.
- [ ] Local transcription (faster-whisper) with word timestamps → TXT/SRT/VTT/JSON.
- [ ] Speaker diarization with neutral labels; reviewed identity mapping.
- [ ] Frame extraction, gallery, timestamp-linked navigation.

## Phase 6 — Dossiers & cross-reference

- [ ] Entity model (people/lawyers/firms/orgs/proceedings/police records…).
- [ ] Assertion/provenance table (section 21.1); relationships with sources.
- [ ] Dynamic dossier HTML views; export to PDF/DOCX/JSON/CSV.
- [ ] Master + per-entity chronologies; relationship graph + accessible table.

## Phase 7 — External AI fallback

- [ ] Provider abstraction (OpenAI first) behind an interface (ARCH-010).
- [ ] Consent screen: items, fragments, sensitive-data categories, cost preview.
- [ ] Redaction before transmission; spending limits; API receipts (API-001..009).

## Phase 8 — Integrity & advanced review

- [ ] Preliminary anomaly indicators (never "forged"): metadata/extension/
      re-encoding/PDF incremental updates, etc. (INT-001..004).
- [ ] Side-by-side, waveform/spectrogram/frame review tools.
- [ ] Contradiction review tasks with both sources and limitations.

## Phase 9 — Professional hardening

- [ ] Roles (admin/cataloger/reviewer/lawyer/expert/read-only/export-only).
- [ ] Encrypted secrets vault; optional at-rest encryption; backup/restore.
- [ ] Signed Windows installer/bootstrapper; pinned dependency manifest.
- [ ] WCAG 2.2 AA accessibility audit; user/admin manuals (pt-BR + en).
- [ ] LGPD/privacy configuration screen and exportable processing record.
