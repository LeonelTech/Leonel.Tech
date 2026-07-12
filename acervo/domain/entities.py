"""Entity model for Fase 6 (Dossiers & Cross-reference).

Core entities: people, lawyers, law firms, proceedings, locations, events.
Everything connects via relationships with provenance and confidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class EntityKind(str, Enum):
    """Every catalogable entity type (section 8)."""

    PERSON = "person"
    LAWYER = "lawyer"
    LAW_FIRM = "law_firm"
    ORGANIZATION = "organization"
    JUDICIAL_PROCEEDING = "judicial_proceeding"
    POLICE_RECORD = "police_record"
    CONTRACT = "contract"
    TRANSACTION = "transaction"
    PROPERTY = "property"
    LOCATION = "location"
    VEHICLE = "vehicle"
    DEVICE = "device"
    EVENT = "event"
    COMMUNICATION = "communication"
    CLAIM = "claim"


class ConfidenceLevel(str, Enum):
    """Confidence in an extracted fact or relationship (section 8)."""

    CONFIRMED = "confirmed"  # user or professional confirmed
    USER_CONFIRMED = "user_confirmed"
    INFERRED = "inferred"
    PROBABLE = "probable"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class Identifier:
    """An identifier (CPF, CNPJ, OAB, CNJ number, etc.)."""

    value: str
    kind: str  # cpf, cnpj, oab, cnj_number, plate, etc.
    extracted_from_file: str | None = None  # file ID if known
    is_verified: bool = False


@dataclass(frozen=True)
class Assertion:
    """A cataloged fact with full provenance (section 21.1).

    Example: "Person X works at Organization Y" with source file + confidence.
    """

    subject_id: str  # entity ID
    predicate: str  # "works_at", "represents", "authored", "mentioned_in"…
    object_id: str | None = None  # target entity ID if linking to another entity
    literal_value: str | None = None  # or a string value if not linking

    source_file_id: str | None = None
    source_page: int | None = None
    source_timestamp_start: float | None = None  # video/audio
    source_timestamp_end: float | None = None
    source_frame_start: int | None = None  # video frame
    source_frame_end: int | None = None

    extraction_method: str = "manual"  # manual, ocr, nlp, external_ai
    confidence: ConfidenceLevel = ConfidenceLevel.UNVERIFIED
    contradicted_by_id: str | None = None  # if contradicted, point to conflicting assertion
    review_status: str = "pending"  # pending, approved, rejected
    limitations: str | None = None  # e.g., "low OCR confidence", "partial match"
    notes: str | None = None


@dataclass(frozen=True)
class Relationship:
    """Connection between two entities with temporal and contextual info."""

    source_entity_id: str
    target_entity_id: str
    relationship_type: str  # "represented_by", "employed_at", "parent_of", "claims_against"…
    start_date: str | None = None  # ISO 8601 if known
    end_date: str | None = None
    role: str | None = None  # "lawyer", "defendant", "witness"…
    confidence: ConfidenceLevel = ConfidenceLevel.UNVERIFIED
    is_confirmed: bool = False
