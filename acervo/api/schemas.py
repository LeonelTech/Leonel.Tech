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
