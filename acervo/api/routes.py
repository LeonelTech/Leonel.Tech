"""API routes for the preservation MVP."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from acervo import __version__
from acervo.api import schemas
from acervo.db.base import session_scope
from acervo.db.models import (
    CatalogingSession,
    Collection,
    Entity,
    Assertion,
    Relationship,
    Chronology,
    File,
    SourceMedia,
    IntegrityFinding,
    Contradiction,
)
from acervo.domain.entities import EntityKind, ConfidenceLevel
from acervo.domain.paths import PathSafetyError
from acervo.i18n import AVAILABLE_LOCALES, DEFAULT_LOCALE, load_locale
from acervo.services import sessions as svc
from acervo.services import dossiers as dossier_svc
from acervo.services import integrity as integrity_svc
from acervo.services import transcription as transcription_svc

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


# ===== Phase 6: Dossiers =====


@router.post("/entities", response_model=schemas.EntityResponse)
def create_entity(req: schemas.CreateEntityRequest) -> schemas.EntityResponse:
    with session_scope() as session:
        col = _get_collection(session, req.collection_identifier)
        try:
            kind = EntityKind(req.kind)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid entity kind: {req.kind}")

        entity = dossier_svc.create_entity(
            session, col, kind, req.name, req.description
        )
        return schemas.EntityResponse(
            identifier=entity.identifier,
            kind=entity.kind,
            name=entity.name,
            display_name=entity.display_name,
            description=entity.description,
        )


@router.get("/entities/{collection_identifier}", response_model=list[schemas.EntityResponse])
def list_entities(collection_identifier: str) -> list[schemas.EntityResponse]:
    with session_scope() as session:
        col = _get_collection(session, collection_identifier)
        entities = session.execute(
            select(Entity).where(Entity.collection_id == col.id).order_by(Entity.name)
        ).scalars().all()

        return [
            schemas.EntityResponse(
                identifier=e.identifier,
                kind=e.kind,
                name=e.name,
                display_name=e.display_name,
                description=e.description,
            )
            for e in entities
        ]


@router.get("/entities/{collection_identifier}/{entity_identifier}")
def get_entity_dossier(
    collection_identifier: str, entity_identifier: str
) -> schemas.DossierResponse:
    with session_scope() as session:
        col = _get_collection(session, collection_identifier)
        entity = session.execute(
            select(Entity).where(
                Entity.collection_id == col.id,
                Entity.identifier == entity_identifier
            )
        ).scalar_one_or_none()

        if entity is None:
            raise HTTPException(status_code=404, detail="entity not found")

        dossier = dossier_svc.get_entity_dossier(session, entity)

        assertions = [
            schemas.AssertionResponse(
                subject_identifier=entity_identifier,
                predicate=a.predicate,
                object_entity_identifier=None,
                literal_value=a.literal_value,
                confidence=a.confidence,
                extraction_method=a.extraction_method,
                review_status=a.review_status,
            )
            for a in dossier["assertions"]
        ]

        relationships = [
            schemas.RelationshipResponse(
                source_identifier=entity_identifier,
                target_identifier="",  # Would need to fetch target entity
                relationship_type=r.relationship_type,
                role=r.role,
                confidence=r.confidence,
            )
            for r in dossier["relationships"]
        ]

        return schemas.DossierResponse(
            entity=schemas.EntityResponse(
                identifier=entity.identifier,
                kind=entity.kind,
                name=entity.name,
                display_name=entity.display_name,
                description=entity.description,
            ),
            assertions=assertions,
            relationships=relationships,
        )


@router.post("/assertions", response_model=schemas.AssertionResponse)
def add_assertion(req: schemas.AddAssertionRequest) -> schemas.AssertionResponse:
    with session_scope() as session:
        col = _get_collection(session, req.collection_identifier)
        subject = session.execute(
            select(Entity).where(
                Entity.collection_id == col.id,
                Entity.identifier == req.subject_identifier
            )
        ).scalar_one_or_none()

        if subject is None:
            raise HTTPException(status_code=404, detail="subject entity not found")

        try:
            confidence = ConfidenceLevel(req.confidence)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid confidence: {req.confidence}")

        object_entity = None
        if req.object_entity_identifier:
            object_entity = session.execute(
                select(Entity).where(
                    Entity.collection_id == col.id,
                    Entity.identifier == req.object_entity_identifier
                )
            ).scalar_one_or_none()

        assertion = dossier_svc.add_assertion(
            session,
            subject,
            req.predicate,
            object_entity=object_entity,
            literal_value=req.literal_value,
            confidence=confidence,
            extraction_method=req.extraction_method,
        )

        return schemas.AssertionResponse(
            subject_identifier=req.subject_identifier,
            predicate=assertion.predicate,
            object_entity_identifier=req.object_entity_identifier,
            literal_value=assertion.literal_value,
            confidence=assertion.confidence,
            extraction_method=assertion.extraction_method,
            review_status=assertion.review_status,
        )


# ===== Phase 8: Integrity =====


@router.get("/integrity/findings")
def list_integrity_findings(
    collection_identifier: str | None = None, severity: str | None = None
) -> list[schemas.IntegrityFindingResponse]:
    with session_scope() as session:
        query = select(IntegrityFinding)

        if collection_identifier:
            col = _get_collection(session, collection_identifier)
            query = query.where(File.collection_id == col.id).join(File)

        if severity:
            query = query.where(IntegrityFinding.severity == severity)

        findings = session.execute(query.order_by(IntegrityFinding.id.desc())).scalars().all()

        return [
            schemas.IntegrityFindingResponse(
                file_identifier="",  # Would need to fetch file
                anomaly_kind=f.anomaly_kind,
                severity=f.severity,
                tool=f.tool,
                confidence=f.confidence,
                description=f.description,
                location=f.location,
                benign_explanations=[] if not f.benign_explanations else __import__('json').loads(f.benign_explanations),
                review_status=f.review_status,
            )
            for f in findings
        ]


@router.get("/integrity/contradictions")
def list_contradictions(
    collection_identifier: str | None = None,
) -> list[schemas.ContradictionResponse]:
    with session_scope() as session:
        if collection_identifier:
            col = _get_collection(session, collection_identifier)
            query = select(Contradiction).join(
                Assertion, Contradiction.assertion_1_id == Assertion.id
            ).where(Assertion.subject.has(Entity.collection_id == col.id))
        else:
            query = select(Contradiction)

        contradictions = session.execute(query.order_by(Contradiction.id.desc())).scalars().all()

        return [
            schemas.ContradictionResponse(
                assertion_1_subject="",
                assertion_1_predicate="",
                assertion_2_subject="",
                assertion_2_predicate="",
                conflict_type=c.conflict_type,
                confidence=c.confidence,
                review_status=c.review_status,
            )
            for c in contradictions
        ]


# ===== Relationships & Chronology =====


@router.post("/relationships", response_model=schemas.RelationshipResponse)
def link_entities(req: schemas.LinkEntitiesRequest) -> schemas.RelationshipResponse:
    with session_scope() as session:
        col = _get_collection(session, req.collection_identifier)

        source = session.execute(
            select(Entity).where(
                Entity.collection_id == col.id,
                Entity.identifier == req.source_identifier
            )
        ).scalar_one_or_none()

        if source is None:
            raise HTTPException(status_code=404, detail="source entity not found")

        target = session.execute(
            select(Entity).where(
                Entity.collection_id == col.id,
                Entity.identifier == req.target_identifier
            )
        ).scalar_one_or_none()

        if target is None:
            raise HTTPException(status_code=404, detail="target entity not found")

        try:
            confidence = ConfidenceLevel(req.confidence)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid confidence: {req.confidence}")

        rel = dossier_svc.link_entities(
            session,
            source,
            target,
            req.relationship_type,
            role=req.role,
            confidence=confidence,
        )

        return schemas.RelationshipResponse(
            source_identifier=req.source_identifier,
            target_identifier=req.target_identifier,
            relationship_type=rel.relationship_type,
            role=rel.role,
            confidence=rel.confidence,
        )


@router.get("/relationships/{collection_identifier}")
def list_relationships(collection_identifier: str) -> list[schemas.RelationshipResponse]:
    with session_scope() as session:
        col = _get_collection(session, collection_identifier)
        rels = session.execute(
            select(Relationship).join(
                Entity, Relationship.source_id == Entity.id
            ).where(Entity.collection_id == col.id)
        ).scalars().all()

        return [
            schemas.RelationshipResponse(
                source_identifier="",  # Would need to fetch
                target_identifier="",  # Would need to fetch
                relationship_type=r.relationship_type,
                role=r.role,
                confidence=r.confidence,
            )
            for r in rels
        ]


@router.post("/chronology", response_model=schemas.ChronologyResponse)
def add_chronology(req: schemas.AddChronologyRequest) -> schemas.ChronologyResponse:
    with session_scope() as session:
        col = _get_collection(session, req.collection_identifier)

        entity = None
        if req.entity_identifier:
            entity = session.execute(
                select(Entity).where(
                    Entity.collection_id == col.id,
                    Entity.identifier == req.entity_identifier
                )
            ).scalar_one_or_none()

            if entity is None:
                raise HTTPException(status_code=404, detail="entity not found")

        event = dossier_svc.add_chronology_event(
            session,
            col,
            req.event_date,
            req.event_type,
            req.description,
            entity=entity,
            source_file=None,
        )

        return schemas.ChronologyResponse(
            event_date=event.event_date,
            event_type=event.event_type,
            description=event.description,
            entity_identifier=req.entity_identifier,
            confidence=event.confidence,
        )


@router.get("/chronology/{collection_identifier}")
def list_chronology(
    collection_identifier: str,
    entity_identifier: str | None = None,
) -> list[schemas.ChronologyResponse]:
    with session_scope() as session:
        col = _get_collection(session, collection_identifier)

        query = select(Chronology).where(Chronology.collection_id == col.id)

        if entity_identifier:
            entity = session.execute(
                select(Entity).where(
                    Entity.collection_id == col.id,
                    Entity.identifier == entity_identifier
                )
            ).scalar_one_or_none()

            if entity:
                query = query.where(Chronology.entity_id == entity.id)

        events = session.execute(
            query.order_by(Chronology.event_date)
        ).scalars().all()

        return [
            schemas.ChronologyResponse(
                event_date=e.event_date,
                event_type=e.event_type,
                description=e.description,
                entity_identifier=entity_identifier,
                confidence=e.confidence,
            )
            for e in events
        ]


# ===== Phase 7: Transcription =====


@router.post("/transcription", response_model=schemas.TranscriptionResponse)
def transcribe_audio(req: schemas.TranscriptionRequest) -> schemas.TranscriptionResponse:
    with session_scope() as session:
        file = session.execute(
            select(File).where(File.identifier == req.file_identifier)
        ).scalar_one_or_none()

        if file is None:
            raise HTTPException(status_code=404, detail="file not found")

        # Check if file is audio
        if not file.mime_type or not file.mime_type.startswith("audio/"):
            raise HTTPException(
                status_code=400,
                detail=f"File is not audio: {file.mime_type}"
            )

        try:
            result = transcription_svc.TranscriptionService.transcribe_audio(
                file.validated_master_path or file.source_path,
                language=req.language,
            )

            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])

            return schemas.TranscriptionResponse(
                file_identifier=req.file_identifier,
                text=result["text"],
                language=result["language"],
                segments=[
                    schemas.TranscriptionSegment(
                        start=seg["start"],
                        end=seg["end"],
                        text=seg["text"],
                    )
                    for seg in result.get("segments", [])
                ],
                confidence=result["confidence"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


@router.post("/diarization", response_model=schemas.DiarizationResponse)
def detect_speakers(req: schemas.SpeakerDiarizationRequest) -> schemas.DiarizationResponse:
    with session_scope() as session:
        file = session.execute(
            select(File).where(File.identifier == req.file_identifier)
        ).scalar_one_or_none()

        if file is None:
            raise HTTPException(status_code=404, detail="file not found")

        # Check if file is audio or video
        if not file.mime_type or not (
            file.mime_type.startswith("audio/") or file.mime_type.startswith("video/")
        ):
            raise HTTPException(
                status_code=400,
                detail=f"File is not audio or video: {file.mime_type}"
            )

        try:
            result = transcription_svc.TranscriptionService.detect_speakers(
                file.validated_master_path or file.source_path,
                num_speakers=req.num_speakers,
            )

            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])

            return schemas.DiarizationResponse(
                file_identifier=req.file_identifier,
                segments=[
                    schemas.SpeakerSegment(
                        speaker=seg["speaker"],
                        start=seg["start"],
                        end=seg["end"],
                        text=seg.get("text", ""),
                    )
                    for seg in result.get("segments", [])
                ],
                total_speech_duration=result.get("total_speech_duration", 0),
                num_speakers_detected=result.get("num_speakers_detected", 0),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Diarization error: {str(e)}")
