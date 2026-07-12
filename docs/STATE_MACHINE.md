# File cataloging state machine

Implemented in `acervo/domain/states.py`. Transitions are validated: any move
not explicitly allowed raises `InvalidTransition`, so a resumed session can
never skip a durable checkpoint (JOB-002/003).

## Happy path

```
DISCOVERED → QUEUED → SOURCE_HASHED → COPYING → COPY_VALIDATED
   → METADATA_EXTRACTED → CLASSIFIED → CONTENT_PROCESSED
   → INDEXED → CATALOGED → COMPLETED
```

For the **preservation MVP**, `COPY_VALIDATED` is the terminal success state; the
stages from `METADATA_EXTRACTED` onward are reserved for later phases (documents,
multimedia, dossiers) and already exist in the enum so the machine extends
without a breaking change.

## Failure / review states

Reachable from the relevant stages; they hold the file until a human decision or
retry policy moves it forward.

| State | Entered from | Meaning |
|-------|--------------|---------|
| `read_failed` | discovery/hashing | source could not be read |
| `copy_failed` | copying | copy raised an OS error |
| `hash_mismatch` | copying | destination hash ≠ source hash |
| `corrupt` | preservation | content detected as corrupt |
| `unsupported` | preservation | extension/content unsupported |
| `partial_analysis` | analysis | some content processed, some not |
| `low_confidence` | analysis | OCR/transcription below threshold |
| `review_required` | analysis | needs a human decision |
| `awaiting_api` | analysis | queued for external AI (with consent) |
| `awaiting_human_decision` | analysis | blocked on a person |
| `canceled` | any | user canceled — terminal |
| `quarantined` | any failure | isolated for review — terminal |

From a recoverable review/failure state the file may go back to `QUEUED`
(retry), or to `QUARANTINED` / `CANCELED` (terminal). `COMPLETED`,
`QUARANTINED` and `CANCELED` have no outgoing transitions.

## No-reprocessing rule (JOB-006)

`reached_checkpoint(state, checkpoint)` returns whether a file is at or beyond a
given happy-path checkpoint. The session runner uses this to skip files already
at `COPY_VALIDATED`/`COMPLETED`, so re-running is idempotent. Reprocessing with a
new pipeline/model version will create a *new* analysis version rather than
deleting the old one (future phases).
