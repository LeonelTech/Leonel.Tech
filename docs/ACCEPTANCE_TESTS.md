# Acceptance criteria — preservation pipeline

Mapping of the specification's system-wide acceptance criteria (section 30) to
their automated coverage in this repository. Criteria for later phases are
listed as **deferred** and tracked in `docs/BACKLOG.md`.

| ID | Criterion (abridged) | Status | Covered by |
|----|----------------------|--------|-----------|
| ACC-001 | 20+ GB collection inventoried, copied, validated, **interrupted and resumed** without altering source or repeating work | ✅ core proven at small scale | `test_sessions.py::test_no_reprocessing_on_rerun`, `::test_resume_after_new_files_added`; performance-at-scale is a Phase 2 hardening item |
| ACC-002 | Return client drive after copying; continue on validated copies; preservation guidance/return docs | ◑ partial | master copies + `returned_to_owner` flag exist; return-of-media report is deferred |
| ACC-003 | Same content / different name detected as duplicate; same name / different content treated as distinct | ✅ | `test_sessions.py::test_full_session_validates_and_dedups` |
| ACC-004 | A document relatable to person/lawyer/firm/proceeding/report without duplicating the master | ⏳ deferred | entities/dossiers (Phase 6) |
| ACC-005 | Search a phrase and open the exact page/timestamp | ⏳ deferred | search/index (documents & multimedia phases) |
| ACC-006 | Low-confidence OCR/transcription is marked and can be retried/escalated | ⏳ deferred | Phases 4–5, 7 |
| ACC-007 | No external API request without visible authorization + receipt | ⏳ deferred | Phase 7 |
| ACC-008 | Dossiers/reports differentiate facts, allegations, inferences, metadata, descriptions, confirmations | ⏳ deferred | Phases 6, 8 |
| ACC-009 | pt-BR default; switching to English does not change identifiers or break data | ✅ | identifiers are language-neutral (`test_domain.py`); locales in `acervo/i18n` |
| ACC-010 | Keyboard-operable and screen-reader usable core workflows | ◑ partial | accessible web shell present; full A11Y audit is Phase 9 |

## Preservation-specific guarantees (verified)

- **Originals never modified** — `test_sessions.py::test_original_files_never_modified`
  hashes the whole source tree before and after a run and asserts equality.
- **Hash mismatch never accepted** — `test_preservation.py::test_copy_and_verify_detects_corruption`
  simulates a faulty medium; the copy is not promoted.
- **Manifest is self-verifiable** — `test_sessions.py::test_manifest_written_and_self_hashed`
  recomputes and matches the recorded manifest SHA-256.
- **Destination-inside-source rejected** — `test_domain.py` and `test_api.py`.
- **Audit trail records key events** — `test_sessions.py::test_audit_trail_records_key_events`.

Run everything with `python -m pytest` (25 tests).

Legend: ✅ met · ◑ partially met · ⏳ deferred to a later phase.
