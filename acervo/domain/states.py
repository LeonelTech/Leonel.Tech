"""File cataloging state machine (JOB-002, section 7).

The happy path is:

    DISCOVERED -> QUEUED -> SOURCE_HASHED -> COPYING -> COPY_VALIDATED
    -> METADATA_EXTRACTED -> CLASSIFIED -> CONTENT_PROCESSED
    -> INDEXED -> CATALOGED -> COMPLETED

Failure / review states can be entered from many points and are terminal
until a human or a retry policy moves them forward. Transitions are validated
so a resumed session can never skip a durable checkpoint (JOB-003).
"""

from __future__ import annotations

from enum import Enum


class FileState(str, Enum):
    # --- happy path ---
    DISCOVERED = "discovered"
    QUEUED = "queued"
    SOURCE_HASHED = "source_hashed"
    COPYING = "copying"
    COPY_VALIDATED = "copy_validated"
    METADATA_EXTRACTED = "metadata_extracted"
    CLASSIFIED = "classified"
    CONTENT_PROCESSED = "content_processed"
    INDEXED = "indexed"
    CATALOGED = "cataloged"
    COMPLETED = "completed"

    # --- failure / review (JOB-002) ---
    READ_FAILED = "read_failed"
    COPY_FAILED = "copy_failed"
    HASH_MISMATCH = "hash_mismatch"
    CORRUPT = "corrupt"
    UNSUPPORTED = "unsupported"
    PARTIAL_ANALYSIS = "partial_analysis"
    LOW_CONFIDENCE = "low_confidence"
    REVIEW_REQUIRED = "review_required"
    AWAITING_API = "awaiting_api"
    AWAITING_HUMAN_DECISION = "awaiting_human_decision"
    CANCELED = "canceled"
    QUARANTINED = "quarantined"


# Ordered happy-path checkpoints used to compute "no reprocessing" and resume.
HAPPY_PATH: tuple[FileState, ...] = (
    FileState.DISCOVERED,
    FileState.QUEUED,
    FileState.SOURCE_HASHED,
    FileState.COPYING,
    FileState.COPY_VALIDATED,
    FileState.METADATA_EXTRACTED,
    FileState.CLASSIFIED,
    FileState.CONTENT_PROCESSED,
    FileState.INDEXED,
    FileState.CATALOGED,
    FileState.COMPLETED,
)

# Review/failure states reachable while copying or hashing the source.
_PRESERVATION_FAILURES = frozenset(
    {
        FileState.READ_FAILED,
        FileState.COPY_FAILED,
        FileState.HASH_MISMATCH,
        FileState.CORRUPT,
        FileState.UNSUPPORTED,
        FileState.QUARANTINED,
        FileState.CANCELED,
    }
)

# Review/failure states reachable during content analysis.
_ANALYSIS_REVIEW = frozenset(
    {
        FileState.PARTIAL_ANALYSIS,
        FileState.LOW_CONFIDENCE,
        FileState.REVIEW_REQUIRED,
        FileState.AWAITING_API,
        FileState.AWAITING_HUMAN_DECISION,
        FileState.CANCELED,
        FileState.QUARANTINED,
    }
)


def _happy_successors(state: FileState) -> frozenset[FileState]:
    idx = HAPPY_PATH.index(state)
    if idx + 1 < len(HAPPY_PATH):
        return frozenset({HAPPY_PATH[idx + 1]})
    return frozenset()


# Explicit allowed transitions. Anything not listed is rejected.
ALLOWED_TRANSITIONS: dict[FileState, frozenset[FileState]] = {}
for _state in HAPPY_PATH:
    _targets = set(_happy_successors(_state))
    # Preservation stages may fail into preservation-failure states.
    if _state in (
        FileState.DISCOVERED,
        FileState.QUEUED,
        FileState.SOURCE_HASHED,
        FileState.COPYING,
    ):
        _targets |= _PRESERVATION_FAILURES
    # Analysis stages may branch into review states.
    if _state in (
        FileState.COPY_VALIDATED,
        FileState.METADATA_EXTRACTED,
        FileState.CLASSIFIED,
        FileState.CONTENT_PROCESSED,
        FileState.INDEXED,
    ):
        _targets |= _ANALYSIS_REVIEW
    ALLOWED_TRANSITIONS[_state] = frozenset(_targets)

# From a review/failure state, a human decision or retry can re-queue the file
# or quarantine it permanently. Quarantined/canceled/completed are terminal.
for _state in _PRESERVATION_FAILURES | _ANALYSIS_REVIEW:
    if _state in (FileState.QUARANTINED, FileState.CANCELED):
        ALLOWED_TRANSITIONS.setdefault(_state, frozenset())
    else:
        ALLOWED_TRANSITIONS.setdefault(
            _state,
            frozenset({FileState.QUEUED, FileState.QUARANTINED, FileState.CANCELED}),
        )
ALLOWED_TRANSITIONS.setdefault(FileState.COMPLETED, frozenset())


class InvalidTransition(ValueError):
    """Raised when a state transition is not permitted."""


def can_transition(current: FileState, target: FileState) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


def assert_transition(current: FileState, target: FileState) -> None:
    if not can_transition(current, target):
        raise InvalidTransition(f"{current.value} -> {target.value} is not allowed")


def is_terminal(state: FileState) -> bool:
    return not ALLOWED_TRANSITIONS.get(state, frozenset())


def reached_checkpoint(state: FileState, checkpoint: FileState) -> bool:
    """True if ``state`` is at or beyond ``checkpoint`` on the happy path.

    Used by the no-reprocessing logic (JOB-006) and resume (JOB-003). Review
    states are not on the happy path and always return False.
    """
    if state not in HAPPY_PATH or checkpoint not in HAPPY_PATH:
        return False
    return HAPPY_PATH.index(state) >= HAPPY_PATH.index(checkpoint)
