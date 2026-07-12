"""API routes for the preservation MVP."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from acervo import __version__
from acervo.api import schemas
from acervo.db.base import session_scope
from acervo.db.models import CatalogingSession, Collection, File, SourceMedia
from acervo.domain.paths import PathSafetyError
from acervo.i18n import AVAILABLE_LOCALES, DEFAULT_LOCALE, load_locale
from acervo.services import sessions as svc

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "Acervo", "version": __version__}


@router.get("/locales")
def locales() -> dict[str, object]:
    return {"default": DEFAULT_LOCALE, "available": list(AVAILABLE_LOCALES)}


@router.get("/locales/{locale}")
def locale_messages(locale: str) -> dict[str, str]:
    return load_locale(locale)


def _get_collection(session, identifier: str) -> Collection:
    obj = session.execute(
        select(Collection).where(Collection.identifier == identifier)
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail=f"collection {identifier} not found")
    return obj


@router.post("/collections", response_model=schemas.CollectionResponse)
def create_collection(req: schemas.CreateCollectionRequest) -> schemas.CollectionResponse:
    with session_scope() as session:
        col = svc.create_collection(session, req.name, req.description)
        return schemas.CollectionResponse(
            identifier=col.identifier, name=col.name, description=col.description
        )


@router.post("/media", response_model=schemas.MediaResponse)
def register_media(req: schemas.RegisterMediaRequest) -> schemas.MediaResponse:
    with session_scope() as session:
        col = _get_collection(session, req.collection_identifier)
        media = svc.register_source_media(session, col, req.label, req.source_root)
        return schemas.MediaResponse(
            identifier=media.identifier, label=media.label, source_root=media.source_root
        )


@router.post("/sessions", response_model=schemas.SessionResponse)
def start_session(req: schemas.StartSessionRequest) -> schemas.SessionResponse:
    with session_scope() as session:
        col = _get_collection(session, req.collection_identifier)
        media = session.execute(
            select(SourceMedia).where(SourceMedia.identifier == req.media_identifier)
        ).scalar_one_or_none()
        if media is None:
            raise HTTPException(status_code=404, detail="source media not found")
        try:
            cat = svc.start_session(
                session,
                col,
                media,
                source_root=req.source_root,
                destination_root=req.destination_root,
                profile=req.profile,
            )
        except PathSafetyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return schemas.SessionResponse(
            identifier=cat.identifier,
            status=cat.status,
            source_root=cat.source_root,
            destination_root=cat.destination_root,
            profile=cat.profile,
        )


@router.post("/sessions/{identifier}/run", response_model=schemas.PreservationStatsResponse)
def run_session(identifier: str) -> schemas.PreservationStatsResponse:
    with session_scope() as session:
        cat = session.execute(
            select(CatalogingSession).where(CatalogingSession.identifier == identifier)
        ).scalar_one_or_none()
        if cat is None:
            raise HTTPException(status_code=404, detail="session not found")
        cat_id = cat.id
    stats = svc.run_preservation(cat_id)
    return schemas.PreservationStatsResponse(
        session_identifier=identifier,
        discovered=stats.discovered,
        already_done=stats.already_done,
        validated=stats.validated,
        duplicates=stats.duplicates,
        quarantined=stats.quarantined,
        bytes_validated=stats.bytes_validated,
        errors=stats.errors,
    )


@router.get("/sessions/{identifier}/files", response_model=schemas.FileListResponse)
def list_files(identifier: str) -> schemas.FileListResponse:
    with session_scope() as session:
        cat = session.execute(
            select(CatalogingSession).where(CatalogingSession.identifier == identifier)
        ).scalar_one_or_none()
        if cat is None:
            raise HTTPException(status_code=404, detail="session not found")
        files = (
            session.execute(select(File).where(File.session_id == cat.id).order_by(File.id))
            .scalars()
            .all()
        )
        id_by_pk = {f.id: f.identifier for f in files}
        rows = [
            schemas.FileRow(
                identifier=f.identifier,
                original_filename=f.original_filename,
                source_path=f.source_path,
                validated_master_path=f.validated_master_path,
                size_bytes=f.size_bytes,
                mime_type=f.mime_type,
                state=f.state,
                content_sha256=f.content_sha256,
                duplicate_of=id_by_pk.get(f.duplicate_of_id) if f.duplicate_of_id else None,
            )
            for f in files
        ]
        return schemas.FileListResponse(
            session_identifier=identifier, file_count=len(rows), files=rows
        )
