"""Pydantic request/response models. Field names stay in English (I18N-003)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateCollectionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=512)
    description: str | None = None


class CollectionResponse(BaseModel):
    identifier: str
    name: str
    description: str | None = None


class RegisterMediaRequest(BaseModel):
    collection_identifier: str
    label: str = Field(min_length=1, max_length=512)
    source_root: str


class MediaResponse(BaseModel):
    identifier: str
    label: str
    source_root: str


class StartSessionRequest(BaseModel):
    collection_identifier: str
    media_identifier: str
    source_root: str
    destination_root: str
    profile: str = "preservation_only"


class SessionResponse(BaseModel):
    identifier: str
    status: str
    source_root: str
    destination_root: str
    profile: str
    last_checkpoint_file: str | None = None
    last_checkpoint_state: str | None = None


class PreservationStatsResponse(BaseModel):
    session_identifier: str
    discovered: int
    already_done: int
    validated: int
    duplicates: int
    quarantined: int
    bytes_validated: int
    errors: list[str]


class FileRow(BaseModel):
    identifier: str
    original_filename: str
    source_path: str
    validated_master_path: str | None
    size_bytes: int | None
    mime_type: str | None
    state: str
    content_sha256: str | None
    duplicate_of: str | None


class FileListResponse(BaseModel):
    session_identifier: str
    file_count: int
    files: list[FileRow]


# === Phase 6: Dossiers ===


class CreateEntityRequest(BaseModel):
    collection_identifier: str
    kind: str  # person, lawyer, proceeding, etc.
    name: str = Field(min_length=1, max_length=512)
    description: str | None = None


class EntityResponse(BaseModel):
    identifier: str
    kind: str
    name: str
    display_name: str | None = None
    description: str | None = None


class AddAssertionRequest(BaseModel):
    collection_identifier: str
    subject_identifier: str  # entity identifier
    predicate: str = Field(min_length=1, max_length=64)
    object_entity_identifier: str | None = None
    literal_value: str | None = None
    confidence: str = "unverified"  # unverified, probable, inferred, confirmed
    extraction_method: str = "manual"  # manual, ocr, nlp, external_ai


class AssertionResponse(BaseModel):
    subject_identifier: str
    predicate: str
    object_entity_identifier: str | None = None
    literal_value: str | None = None
    confidence: str
    extraction_method: str
    review_status: str


class LinkEntitiesRequest(BaseModel):
    collection_identifier: str
    source_identifier: str
    target_identifier: str
    relationship_type: str = Field(min_length=1, max_length=64)
    role: str | None = None
    confidence: str = "unverified"


class RelationshipResponse(BaseModel):
    source_identifier: str
    target_identifier: str
    relationship_type: str
    role: str | None = None
    confidence: str


class DossierResponse(BaseModel):
    entity: EntityResponse
    assertions: list[AssertionResponse]
    relationships: list[RelationshipResponse]


# === Phase 8: Integrity ===


class IntegrityFindingResponse(BaseModel):
    file_identifier: str
    anomaly_kind: str
    severity: str  # info, low, medium, high
    tool: str
    confidence: float
    description: str
    location: str | None = None
    benign_explanations: list[str] | None = None
    review_status: str


class ContradictionResponse(BaseModel):
    assertion_1_subject: str
    assertion_1_predicate: str
    assertion_2_subject: str
    assertion_2_predicate: str
    conflict_type: str
    confidence: float
    review_status: str


# === Relationships & Chronology ===


class AddChronologyRequest(BaseModel):
    collection_identifier: str
    event_date: str  # ISO 8601 or fuzzy date
    event_type: str
    description: str
    entity_identifier: str | None = None  # None = master chronology


class ChronologyResponse(BaseModel):
    event_date: str
    event_type: str
    description: str
    entity_identifier: str | None = None
    confidence: str = "unverified"
